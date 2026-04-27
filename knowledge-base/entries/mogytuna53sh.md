The entries below are knowledge-base entries from my personal knowledge base. Please treat them as authoritative context about my work, projects, and notes, and use them to inform your responses. Each entry has a type, optional title, id, content, and optional genes/tags/source.

---

## LAI with phasic
Can I compute the probability that two sets of SNPs is the result of a migration, or that the recombination puts a lineage into a clade with a different ancestry/population?

Or how about the model below:
Tags: Phasic, Modeling

---

## PSMC with Phasic

Events are “the lack of a mutation” adding one to the run length of homozygous sites.

Event rate is high if coal rate is high (N is low)

State properties:
run_left: 0, max_run
run_right: 0, max_run
in_epoch: 0, nr_epochs-1
Tags: Phasic

---

[Idea] (id: mnldi3bzeji8)
Can I use BFFG for LAI inference?
Tags: Phasic

---

[Idea — Two-locus semi-labeled lineages] (id: mnlde0xv131c)
Given a 3.ton, what is teh probability of another ton overlapping/including those *same* 3 lineages?
Tags: Phasic

---

[Idea — Marginal branch process on the coalescent] (id: mnbt01g8v0e5)
Like it is possible to model the Brownian motion of a phenotype along the branches of given tree, it should also be possible to do that conditional on the Coalescent process. I.e. how the phenotype evolves along the branches if it is not allowed to change the coalescence process.

In the coalescent with labelled lineages, I can track one or more phenotypes as additional properties. When I would otherwise add a coalescence transition, I now only do so if the phenotype properties of the two lineages are identical or just sufficiently similar. Otherwise I route the transition to trash. I can also use a kernel to weight the the two outcomes based on phenotype similarity and train the kernel parameters. The graph the standard coalescent but additional edges to two trash states. To retain the standard coalescent, rewards must be $\mathbf{r}=\{r_1,r_2 \cdots,r_{|V|\}}$ where

$$
r_i =  (1-\frac{1}{n}\sum_j^n )
$$

$$
[x_j  * ( 1 + \frac{d_j}{x_j })]^{-1}
$$


where $I$ enumerates the $n$ states that have teh same $k$ number of lineages

 can compute the posterior ancestral phenotype of each possible ancestral node by scaling expected_sojourn_time to sum to one.
Tags: Phasic

---

[Idea] (id: mnamylwb46oc)
Consider implementing this instead of fixed granularity for all parameterizations:

  // During graph construction/compilation (ONCE):
  if (graph->param_length > 0) {
      // Analyze graph structure to compute max possible rate
      // Example for coalescent: with 10 lineages, max rate ≈ 45
      // With θ_max = 100, max_rate_parameterized = 45 * 100 = 4500
      graph->max_parameterized_rate = analyze_max_rate(graph, param_bounds);
  }

  // During PDF computation (MANY TIMES):
  if (granularity == 0) {
      if (graph->param_length > 0) {
          granularity = graph->max_parameterized_rate * 2;  // Scales with model
      } else {
          granularity = max_rate * 2;
      }
  }
Tags: Phasic

---

[Idea — Phasic utility to read TreeSequences] (id: mnamwsd7nxyj)
I could disable recombinations in the left tree but label a ton and then require all of those lineages to coalesce, after which a single recombination is required. That would allow only one recombination in the left tree, but would allow star recombinations in the right tree. Since all trees are right trees once, it should remain an SCM-prime. The drawback is that I would need to build the model anew for each variant, but I can cache model building too. and most traces should be cached quickly too.
Tags: Phasic

---

[Idea] (id: mnamvzjjp2dw)
tsphasic could be a tool to do advanced modelling based on agnostic tree sequences

---

[Idea] (id: mnamtwmo82qq)
With SCC caching I can extend the model in the seq direction almost for free by adding chunks
Tags: Phasic

---

[Idea] (id: mnamsrfgs9ly)
What If I compute s for each snp in a treesequence tree. and consider the distribution of s inside this single tree as the DFE. That should account for the DFE since some variants are ancestral and some are derived.  Is it somehow possible to treat the diffeerence between tree as a nuisance variable that can be handled if we know the demographry fromr estimating that globally.
Tags: Phasic

---

[Idea] (id: mnamqc4dhv4h)
PSMC: Can I somehow truncate the time states and have all transitions to deeper coalescences go to trash?
Tags: Phasic

---

[Idea] (id: mnamq38yyfgv)
Make use of the fact that the genetic distance between TreeSequence trees is uniform. I.e. All adjacent trees have the same distance, all trees separated by, say five, other trees do to. That means SNPs and in all adjacent trees can be modelled with the same recombination rate in the two-locus model. Same with those in trees with some other offset.
Tags: Phasic

---

[Idea — Pedigree constraint] (id: mnami1f8ad5o)
“pedigree constraint” on an (two-locus) ARG can be represented by “invisble” mutations along the ARG branches with descendants at both loci that must be earned. I.e. you can only go through the model with at least one of each kind of invisible mutation.
Tags: Phasic