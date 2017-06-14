# sqla_yaml_fixtures

This package allows you to define some data in YAML and load them into a DB. The yaml data should correspond to SQLAlchemy declarative mappers.

Example:

```
User:
  - __key__: joey
    username: joey
    email: joey@example.com
    profile:
      name: Jeffrey

  - __key__: dee
    username: deedee
    email: deedee@example.com

Profile:
  - user: dee
    name: Douglas

Group:
  - name: Ramones
    members: [joey.profile, dee.profile]
```

- The root of YAML contain `mapper` names i.e. `User`
- Every mapper should contain a *list* of instances
- Each instance is mapping of *attribute* -> *value*
- the attributes are taken from the mapper `__init__()` (usually an attributes maps to a column)
- The special field `__key__` can be used to identify this instnace in a relationship reference .i.e. The `Profile.user`
- In a *to-one* relationship the data can be directly nested in the parent data definition
- References can access attributes using a *dot* notaion, i.e. `joey.profile`
- *to-many* relationships can be added as a list of references


The mapper definition for this example is in the test file.
