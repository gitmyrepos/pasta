# PASTA - Python Abstract Syntax Trees Assistant

This Project is a fork of [code2flow](https://github.com/scottrogowski/code2flow).

## The purpose of PASTA

code2flow primarily focused on building [call graphs](https://en.wikipedia.org/wiki/Call_graph), while the focus of this project is to build out a detailed [AST](https://en.wikipedia.org/wiki/Abstract_syntax_tree) diagram. Because of this change in purpose, it seemed right to fork rather than submit major changes to the original project.

Furthermore, the main codebase I currently use is Python. So the focus of this fork will be detailing Python codebases into ASTs, hence (PYTHON abstract syntax trees assistant).

#### Note

Although this project is focused on Python codebases, other code2flow programming languages (JS, Ruby and PHP) should be backwards compatiable (but will only detail a simple call graph). Feel free to fork or submit a PR to add further functionality to JS, Ruby and PHP.

---

The basic algorithm is simple:

1. Translate your source files into ASTs.
1. Find all function definitions.
1. Determine where those functions are called.
1. Connect the dots. 

Pasta is useful for:
- Untangling spaghetti code (The inspiration of the project's name).
- Identifying orphaned functions.
- Identifying arguments passed into functions.
- Identifying variables assigned in functions.
- Provide a better "bird's eye view" of your codebase to get a better     understanding of its architecture 
- Getting new developers up to speed.

Pasta provides a *pretty good estimate* of your project's structure but there may be some issues in identifying nodes, certian variables. These issues will be a further focus of improvement in Pasta.

*(Below: Code2flow running against a subset of itself `code2flow code2flow/engine.py code2flow/python.py --target-function=code2flow --downstream-depth=3`)*

![code2flow running against a subset of itself](https://raw.githubusercontent.com/scottrogowski/code2flow/master/assets/code2flow_output.png)

Installation
------------

```bash
pip3 install code2flow
```

If you don't have it already, you will also need to install graphviz. Installation instructions can be found [here](https://graphviz.org/download/).

Additionally, depending on the language you want to parse, you may need to install additional dependencies:
- JavaScript: [Acorn](https://www.npmjs.com/package/acorn)
- Ruby: [Parser](https://github.com/whitequark/parser)
- PHP: [PHP-Parser](https://github.com/nikic/PHP-Parser)
- Python: No extra dependencies needed

Usage
-----

To generate a DOT file, run something like:

```bash
code2flow mypythonfile.py
```

Or, for Javascript:

```bash
code2flow myjavascriptfile.js
```

You can specify multiple files or import directories:

```bash
code2flow project/directory/source_a.js project/directory/source_b.js
```

```bash
code2flow project/directory/*.js
```

```bash
code2flow project/directory --language js
```

To pull out a subset of the graph, try something like:

```bash
code2flow mypythonfile.py --target-function my_func --upstream-depth=1 --downstream-depth=1
```


There are a ton of command line options, to see them all, run:

```bash
code2flow --help
```

How code2flow works
------------

Code2flow approximates the structure of projects in dynamic languages. It is *not possible* to generate a perfect callgraph for a dynamic language. 

Detailed algorithm:

1. Generate an AST of the source code
2. Recursively separate groups and nodes. Groups are files, modules, or classes. More precisely, groups are namespaces where functions live. Nodes are the functions themselves.
3. For all nodes, identify function calls in those nodes.
4. For all nodes, identify in-scope variables. Attempt to connect those variables to specific nodes and groups. This is where there is some ambiguity in the algorithm because it is impossible to know the types of variables in dynamic languages. So, instead, heuristics must be used.
5. For all calls in all nodes, attempt to find a match from the in-scope variables. This will be an edge.
6. If a definitive match from in-scope variables cannot be found, attempt to find a single match from all other groups and nodes.
7. Trim orphaned nodes and groups.
8. Output results.

Why is it impossible to generate a perfect call graph?
----------------

Consider this toy example in Python
```python
def func_factory(param):
    if param < .5:
        return func_a
    else:
        return func_b

func = func_factory(important_variable)
func()
```

We have no way of knowing whether `func` will point to `func_a` or `func_b` until runtime. In practice, ambiguity like this is common and is present in most non-trivial applications.

Known limitations
-----------------

Code2flow is internally powered by ASTs. Most limitations stem from a token not being named what code2flow expects it to be named.

* All functions without definitions are skipped. This most often happens when a file is not included.
* Functions with identical names in different namespaces are (loudly) skipped. E.g. If you have two classes with identically named methods, code2flow cannot distinguish between these and skips them.
* Imported functions from outside your project directory (including from standard libraries) which share names with your defined functions may not be handled correctly. Instead, when you call the imported function, code2flow will link to your local functions. For example, if you have a function `search()` and call, `import searcher; searcher.search()`, code2flow may link (incorrectly) to your defined function.
* Anonymous or generated functions are skipped. This includes lambdas and factories.
* If a function is renamed, either explicitly or by being passed around as a parameter, it will be skipped.


As an imported library
-----------------

You can work with code2flow as an imported Python library in much the same way as you work with it
from the CLI.

```python
import code2flow
code2flow.code2flow(['path/to/filea', 'path/to/fileb'], 'path/to/outputfile')
```

The keyword arguments to `code2flow.code2flow` are roughly the same as the CLI
parameters. To see all available parameters, refer to the code2flow function in [engine.py](https://github.com/scottrogowski/code2flow/blob/master/code2flow/engine.py).


How to contribute
-----------------------

1. **Open an issue**: Code2flow is not perfect and there is a lot that can be improved. If you find a problem parsing your source that you can identify with a simplified example, please open an issue.
2. **Create a PR**: Even better, if you have a fix for the issue you identified that passes unit tests, please open a PR. 
3. **Add a language**: While dense, each language implementation is between 250-400 lines of code including comments. If you want to implement another language, the existing implementations can be your guide.


Unit tests
------------------

Test coverage is 100%. To run:

```bash
    pip install -r requirements_dev.txt
    make test
```


Feedback / Issues / Contact
-----------------------------

If you have an issue using code2flow or a feature request, please post it in the issues tab.


