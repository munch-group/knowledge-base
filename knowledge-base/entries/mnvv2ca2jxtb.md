
```python
graph = Graph(callback)                                                                       
graph.dyn_ordering = True   # enable dynamic min-degree ordering                              
E = graph.expectation()     # uses dynamic ordering for this graph                            
```

Or set the default for all new graphs via environment variable:                               

```python
os.environ['PHASIC_DYN_ORDERING'] = 1
```

```bash
export PHASIC_DYN_ORDERING=1 
```

