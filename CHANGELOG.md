wfapi changelog
===============

## 0.6.x

Bug fixes:

 - many missing attributes issues, inconsistencies in nodes and avoidable errors fixed.
 - .children and .parent are consistent and are there in all nodes.
 - iterating children from a node is a little more efficient.

Other:
 - many lines of code removed, code is a little cleaner.

Features:

 - call .create, .complete, .edit, .delete directly from node object.

## 0.2.x (?)

Features:

 - support deamon
 - support shared node
 - search like website's keyword (`is:completed`)
 - documentation release
 - support embbeded node

Not Yet:

 - cleanup changlog
 - cleanup readme
 - support all operation for deamon croller
 - support hashtag (for search)
 - support html (for special style like `<b>`)
 - good logging system for track error
 - refresh project with keep node object
 - rollback transaction & undo operation
 - expend node
 - pro features

## 0.2.5 (2015-01-11)

Features:

 - 'collect changed'

## 0.2.0 (2015-01-10)

Features:
 
 - Module system are applyed.

## 0.1.19 (2015-01-05)

Features:

 - Access attribute with node are changed.
 - very simple deamon croller (and unstable)
 
## 0.1.17 (2015-01-05)

Released for pre-alpha use, and registered to PyPI.

Added:

 - setup.py
 - CHANGELOG.md

## 0.1.16 (2015-01-04)

Features:

 - Now support `Connection: keep-alive` for fast api call.
 - Quota control are added.
 - `_collect_operation` are removed. (fast module init)

## 0.1.11 (2015-01-01)

Features:
 
 - changed for easy node access. 
 - raise `WFRuntimeError` if error raised from web.
  - all error except `HTTPError` are subclass of `WFError`

Changed:
 
 - `wfapi_future.py` are renamed to `wfapi.py`

## 0.1.9 (2014-12-30)

Added:

 - `wfapi_future.py`
  - Break legacy code. (but nobody use it!)
  - It provide good name for access attribute
  - etc...

## 0.1.8 (2014-12-29)

Features:

 - New Operation:
  - bulk_create

## 0.1.0 (2014-12-22)

First commit in github.

Features:

 - Workflowy
   - Support login.
   - It support operation with workflowy service.
 - WeakWorkflowy
   - Subclass of Workflowy.
   - It support direct operation with node.
 - WFError
   - This is exception class that raised from this api.
 - Support Transaction at commit only.
 - New Operation:
   - edit
   - create
   - complete
   - uncomplete
   - delete
   - undelete
   - move
