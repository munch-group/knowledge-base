  Here's the cleanest way to think about the four candidate paths in this codebase:
                                               
  Path: A. Direct C-inside-pure_callback (current SVGD)                                                                              
  What runs: GraphBuilder::build() + compute_pmf_and_moments in C++                                                               
  JAX touches it via: pure_callback wrapping the whole call                                                                          
  Status in v2: Modified by v2. Add thread-local persistent phasic::Graph + update_weights(theta); cache                          
    parameterized_reward_compute_graph to disk.                                                                                      
  ────────────────────────────────────────                                                                                        
  Path: B. Python EliminationTrace op DAG (would-be JAX-traceable)                                                                   
  What runs: record_elimination_trace + evaluate_trace_jax                                                                        
  JAX touches it via: JAX traces individual ops, no pure_callback                                                                    
  Status in v2: Untouched by v2. Stays as today. v1 wanted to port real Gaussian elimination here; v2 sets that aside.           
  ────────────────────────────────────────                                                                                           
  Path: C. Python trace + pure_callback to compiled .so                                                                          
  What runs: _generate_cpp_from_trace + _wrap_trace_log_likelihood_for_jax                                                           
  JAX touches it via: pure_callback wrapping the compiled .so                                                                        
  Status in v2: Untouched by v2. Currently broken (ptd_instantiate_from_trace commented out in C).
  ────────────────────────────────────────                                                                                           
  Path: D. Direct Graph.expectation() etc. with cache_trace=True               
  What runs: _ensure_trace → record_elimination_trace (the Python one)                                                               
  JAX touches it via: Not JAX at all — direct user calls      
  Status in v2: Untouched by v2. Cyclic-graph cases stay xfailed.  