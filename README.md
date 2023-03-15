# python property graph (pypg)
Object-oriented descriptor properties designed for capturing complex data-graphs and rich metadata from objects and types.

## Motivation
pypg provides a flexible and terse framework for expressing object schemas, initialization, de/serializiation, and declarative behavior. 

### Example
Consider a directed acyclic graph (DAG) such as: 

     root
     /   \
    1A   1B
     \  /  \
      2A   2B
       \   /
        end

note that 1B is referenced by both 2A and 2B. Naively serializing this object will result in duplication of this data and any upstream nodes, and, upon de-serialiation, the referential integrity will be lost. 

To combat this issue, one can transform the data using adjacency lists or comparison of other unique identifiers to establish relationships.

Using pypg, the DAG above can be expressed like so:

```python

from pypg import Property, PropertyClass
from pypg.transcode import encode, decode


class Node(PropertyClass):
    upstream = Property[list["Node"]]()


root = Node()

layer_1 = [Node(upstream=[root]), Node(upstream=[root])]
layer_2 = [Node(upstream=layer_1), Node(upstream=[layer_1[1]])]
terminal = Node(upstream=layer_2)
```

This structure can be serialized and reconstructed without duplication of object instances, and all identity relationships are preserved.

```python

nodes = [terminal, *layer_2, *layer_1, root]

serialized_nodes = encode(nodes)
copy_nodes = decode(serialized_nodes)

terminal_copy, l2a, l2b, l1a, l1b, root_copy = copy_nodes

assert terminal_copy.upstream[0] is l2a
assert terminal_copy.upstream[1] is l2b
assert l2a.upstream[0] is l1a
assert l2a.upstream[1] is l1b
assert l2b.upstream[0] is l1b
assert l1a.upstream[0] is root_copy
assert l1b.upstream[0] is root_copy
```

Note that in this case it is not necessary to collect all the objects for encoding, the terminal node is sufficient to capture the entire graph.

```python
serialized = encode(terminal)
terminal_copy = decode(serialized)

l2a, l2b = terminal_copy.upstream
l1a, l1b = l2a.upstream
(also_l1b,) = l2b.upstream
assert l1b is also_l1b

(root_copy,) = l1a.upstream
(also_root_copy,) = l1b.upstream
assert root_copy is also_root_copy
```

### Why not dataclasses? 
Aside from cases when object-identity-fidelity is important, dataclasses impose limitations. For example:

```python
from dataclasses import dataclass

@dataclass
class Base:
    a: int = 0

@dataclass
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

If a base class declares a default field, any subsequent fields must also have default values. This violation of the open/closed principle makes dataclasses an unsuitable choice for extendable objects. 

### Why not JSON Schema? 
JSON Schema requires a separate second representation of an object just to describe it. This requires 2 edits to be made for any 1 change, increasing development effort and potential for error. 

### Why descriptors? 
Python descriptors provide a powerful mechanism for encoding type-information and customizing data-handling behaviors. Descriptor classes can be used to extend the semantics of working with object fields with very few limitations. A few examples of those contained in pypg are: 

* the observer pattern
* value validation
* units of measure

By composing decorator-like objects, here called Traits, Property objects provide an expressive but powerful syntax for defining not just data, but also runtime-behaviors that should occur with data access semantics. For more examples, see: 

https://github.com/mattefowler/pypg/blob/main/tests/test_traits.py

https://github.com/mattefowler/pypg/blob/main/tests/test_observable.py

https://github.com/mattefowler/pypg/blob/main/tests/test_overridable.py
