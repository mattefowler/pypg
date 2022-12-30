# python property graph (pypg)
Object-oriented descriptor properties designed capturing complex data-graphs from objects with rich metadata 

## Motivation
pypg provides a flexible and terse framework for expressing object schemas, initialization, de/serializiation, and declarative behavior. 

### Why not dataclasses? 
Dataclasses are well suited for simple data structures but impose severe limitations. For example:

```python
from dataclasses import dataclass

@dataclass
class Base:
    a: int = 0

class Derived(Base): 
    b: int

```
```console
    @dataclass
     ^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.11/lib/python3.11/dataclasses.py", line 1220, in dataclass
    return wrap(cls)
           ^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.11/lib/python3.11/dataclasses.py", line 1210, in wrap
    return _process_class(cls, init, repr, eq, order, unsafe_hash,
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.11/lib/python3.11/dataclasses.py", line 1027, in _process_class
    _init_fn(all_init_fields,
  File "/Library/Frameworks/Python.framework/Versions/3.11/lib/python3.11/dataclasses.py", line 545, in _init_fn
    raise TypeError(f'non-default argument {f.name!r} '
TypeError: non-default argument 'b' follows default argument
python-BaseException
```

If a base class declares a default field, any subsequent fields must also have default values. This violates the open/closed principle thus making dataclasses an unsuitable choice for complex object hierarchies. 

# Why not JSON Schema? 
JSON Schema requires a second representation of an object just to describe it. This requires 2 edits to be made for any 1 change, wasting time and increasing the potential for errors. 

Additionally, JSON Schema's concept of validation is limited to relationships expressible within the 