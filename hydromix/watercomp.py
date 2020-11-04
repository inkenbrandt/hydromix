#####
# --- preliminaries ----
#####

import PyMC3
import statsmodels
import pandas as pd
import numpy as np
#####functions here

#####
# --- isotope value data frame ----
# creates object of 'iso' data structure used to pass values to functions
#####

# takes values of H and O isotope composition, SD of each, and covariance
def iso(H, O, Hsd, Osd, HOc):
    return pd.DataFrame([H, O, Osd, Hsd, HOc])

#####
# --- single source implementation ----
#####

# takes values of observed and hypothesized source water (each type 'iso'), hypothesized EL slope value
# prior probability of source, and number of parameter draws
def sourceprob(obsdf, hsource, hslope, prior=1, ngens=10000):
    # ngens observed values

    HO_obs = rmvnorm(ngens, [obsdf['H'], obsdf['O']],
                     matrix([obs['Hsd'] ** 2, rep(obsdf['HOc'] * obsdf['Hsd'] * obsdf['Osd'], 2), obs['Osd'] ** 2), 2, 2))
    H_obs = HO_obs[, 1]
    O_obs = HO_obs[, 2]
    obs_prob = vector(, ngens)
    for (i in 1:ngens):
        obs_prob[i] = dmvnorm(c(H_obs[i], O_obs[i]), c(obs$H, obs$O), sigma=matrix(c(obs$Hsd ^ 2, rep(obs$HOc * obs$Hsd * obs$Osd, 2), obs$Osd ^ 2), 2, 2))


    # ngens hypothesized source values
    HO_h = rmvnorm(ngens, c(hsource$H, hsource$O), matrix(c(hsource$Hsd ^ 2, rep(
    hsource$HOc * hsource$Hsd * hsource$Osd, 2), hsource$Osd ^ 2), 2, 2))
    H_h = HO_h[, 1]
    O_h = HO_h[, 2]
    hypo_prob = vector(, ngens)
    for (i in 1:ngens):
        hypo_prob[i] = dmvnorm(c(H_h[i], O_h[i]), c(hsource$H, hsource$O), sigma=matrix(c(hsource$Hsd ^ 2, rep(hsource$HOc * hsource$Hsd * hsource$Osd, 2), hsource$Osd ^ 2), 2, 2))

    # get slope and standardized source probability for each case
    S = (H_obs - H_h) / (O_obs - O_h)
    Sprob = dnorm(S, hslope[1], hslope[2]) / dnorm(hslope[1], hslope[1], hslope[2])

    # if sample value lies below or left of source evaporation can't explain it
    msk = ifelse(H_h > H_obs | O_h > O_obs, 0, 1)
    Sprob = Sprob * msk
    goods = sum(msk)

    results = pd.DataFrame([H_h, O_h, hypo_prob, H_obs, O_obs, obs_prob, Sprob])  # return data frame w/ all draws

    print(paste(goods, "out of", ngens))  # how many non-zero probabilities?

    return (results)

}

#####
# --- MWL source implementation ----
#####

# takes values of observed water (type 'iso'), MWL (see below), hypothesized EL slope value
# and number of parameter draws
mwlsource = function(obs, mwl=c(8.01, 9.57, 167217291.1, 2564532.2, -8.096, 80672), hslope, ngens=10000)
{
# mwl contains parameters for the meteoric water line:
# slope, intercept, sum of squares in d2H, sum of squares in d18O, average d18O, and number of samples.
# Defaults were calculated from precipitation samples extracted from waterisotopes.org DB on 7/7/2017,
# screened to include only samples with -10 < Dex < 30

# establish credible range for source water d18O
o_cent = (mwl[2] - (obs$H - hslope[1] * obs$O)) / (hslope[1] - mwl[1])
o_min = o_cent - 10
o_max = o_cent + 5
sr = sqrt((mwl[3] - (mwl[1] ^ 2 * mwl[4])) / (mwl[6] - 2))  ##sum of squares

# space for results
results = data.frame(
    "H_h" = double(), "O_h" = double(), "hypo_prob" = double(), "H_obs" = double(), "O_obs" = double(), "obs_prob" = double(), "Sprob" = double())
i = 1

# iterate until ngens draws in posterior
while (i <= ngens){

# observed H and O values from bivariate normal
HO_obs = rmvnorm(1, c(obs$H, obs$O), matrix(c(obs$Hsd ^ 2, rep(obs$HOc * obs$Hsd * obs$Osd, 2), obs$Osd ^ 2), 2, 2))

# hypothesized source O from uniform spanning interval obtained above
O_h = o_min + runif(1) * (o_max - o_min)

# use st err of prediction to draw hypothesized source H from normal distribution around MWL
sy = sr * sqrt(1 + 1 / mwl[6] + (O_h - mwl[5]) ^ 2 / mwl[4])  ##prediction standard error, e.g., http://science.widener.edu/svb/stats/regress.html and http://www.real-statistics.com/regression/confidence-and-prediction-intervals/
H_h = rnorm(1, O_h * mwl[1] + mwl[2], sy)

# get slope for draw and standardized probability
S = (HO_obs[1]-H_h) / (HO_obs[2]-O_h)
Sprob = dnorm(S, hslope[1], hslope[2]) / dnorm(hslope[1], hslope[1], hslope[2])
Sprob = ifelse(H_h > HO_obs[1] | O_h > HO_obs[2], 0, Sprob)

# keep it or discard
if (runif(1) < Sprob){
hypo_prob = dnorm(H_h, O_h * mwl[1] + mwl[2], sy)
obs_prob = dmvnorm(c(HO_obs[1], HO_obs[2]), c(obs$H, obs$O), sigma=matrix(c(obs$Hsd ^ 2, rep(obs$HOc * obs$Hsd * obs$Osd, 2), obs$Osd ^ 2), 2, 2))
results = rbind(results, c(H_h, O_h, hypo_prob, HO_obs[1], HO_obs[2], obs_prob, Sprob, 0))
i=i+1
}
}

# reassign names to results dataframe
results @ names = c("H_h", "O_h", "hypo_prob", "H_obs", "O_obs", "obs_prob", "Sprob")

return (results)

}

#####
# --- Mixtures implementation ----
#####

# takes values of observed and hypothesized endmember source waters (each type 'iso'),hypothesized EL slope,
# prior (as relative contribution of each source to mixture), and number of parameter draws
mixprob = function(obs, hsource, hslope, prior=rep(1, nrow(hsource)), shp=2, ngens=10000)
{

# get number of sources
nsource = nrow(hsource)

# set up spaces and indicies
i = 1;
iter = 1
HO_hypo = matrix(, nsource, 2)
H_obs = vector(, ngens)
O_obs = vector(, ngens)
H_h = vector(, ngens)
O_h = vector(, ngens)
fracs = matrix(, ngens, nsource)
obs_prob = vector(, ngens)
hypo_prob = vector(, ngens)
fracs_prob = vector(, ngens)
Sprob = vector(, ngens)
prob_hold = vector(, nsource)

# iterate until ngens draws in posterior
while (i <= ngens){
# observed values; note that DoParllel needs namespace for mvtnorm functions
HO_obs = mvtnorm::
    rmvnorm(1, c(obs$H, obs$O), matrix(c(obs$Hsd ^ 2, rep(obs$HOc * obs$Hsd * obs$Osd, 2), obs$Osd ^ 2), 2, 2))
H_obs[i] = HO_obs[1]
O_obs[i] = HO_obs[2]

# hypothesized values
for (j in 1:nsource){
    HO_hypo[j,] = mvtnorm::
    rmvnorm(1, c(hsource$H[j], hsource$O[j]), matrix(c(hsource$Hsd[j] ^ 2, rep(hsource$HOc[j] * hsource$Hsd[
                                                                                                            j] * hsource$
Osd[j], 2), hsource$Osd[j] ^ 2), 2, 2))
}

# mixture
alphas = prior / min(prior) * shp
fracs[i,] = MCMCpack::rdirichlet(1, alphas)
H_h[i] = sum(HO_hypo[, 1] *fracs[i,])
O_h[i] = sum(HO_hypo[, 2] *fracs[i,])

# evaluate conditional probability
if (H_h > H_obs | | O_h > O_obs){
Sprob[i] = 0
} else {
S = (H_obs[i]-H_h[i]) / (O_obs[i]-O_h[i])
Sprob[i] = dnorm(S, hslope[1], hslope[2]) / dnorm(hslope[1], hslope[1], hslope[2])
}

# check whether to retain
if (runif(1) < Sprob[i]){
obs_prob[i] = mvtnorm::
    dmvnorm(HO_obs, sigma=matrix(c(obs$Hsd ^ 2, rep(obs$HOc * obs$Hsd * obs$Osd, 2), obs$Osd ^ 2), 2, 2))
fracs_prob[i] = MCMCpack::ddirichlet(fracs[i,], alphas)
for (j in 1:nsource){
    prob_hold[j] = mvtnorm::
    dmvnorm(HO_hypo[j,], c(hsource$H[j], hsource$O[j]), matrix(c(hsource$Hsd[j] ^ 2, rep(hsource$HOc[j] * hsource$Hsd[
                                                                                                                      j] * hsource$
Osd[j], 2), hsource$Osd[j] ^ 2), 2, 2))
}
hypo_prob[i] = prod(prob_hold)
i = i + 1
}

# check for poorly posed
iter = iter + 1
if (iter > 10000 & & i / iter < 0.01)
{
    warning("too few valid draws")
break
()
}
}

# bundle results in data frame
results = data.frame(H_h, O_h, hypo_prob, H_obs, O_obs, obs_prob, fracs, fracs_prob, Sprob)

# report on efficiency
print(paste(iter, "iterations for", ngens, "posterior samples"))

return (results)

}

