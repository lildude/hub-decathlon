# runtest.py

This script makes it possible to use sets of tests, performed in a similar environment, but with different database / queue / configurations.

### Script flow : 
- call any unit tests function
```
unittest.main()
```
- delete all test database and test cache.
```
tapiriik.database._connection.drop_database("tapiriik_test")
tapiriik.database._connection.drop_database("tapiriik_cache_test")
```
 
# [Back to script summary](000-script-summary.md)

