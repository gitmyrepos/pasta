# PASTA - Python Abstract Syntax Trees Assistant

This Project is a fork of [code2flow](https://github.com/scottrogowski/code2flow).



## The Purpose of PASTA

code2flow primarily focused on building [call graphs](https://en.wikipedia.org/wiki/Call_graph), while the focus of this project is to build out a detailed [AST](https://en.wikipedia.org/wiki/Abstract_syntax_tree) diagram. Because of this change in purpose, it seemed right to fork rather than submit major changes to the original project.

Furthermore, the main codebase I currently use is Python. So the focus of this fork will be detailing Python codebases into ASTs, hence (PYTHON abstract syntax trees assistant).

#### Pasta is useful for:
- Untangling spaghetti code (The inspiration of the project's name).
- Identifying orphaned functions.
- Identifying arguments passed into functions.
- Identifying variables assigned in functions.
- Provide a better "bird's eye view" of your codebase to get a better     understanding of its architecture 
- Getting new developers up to speed.

Pasta provides a *pretty good estimate* of your project's structure but there may be some issues in identifying nodes, certian variables. These issues will be a further focus of improvement in Pasta.

#### Note

Although this project is focused on Python codebases, other code2flow programming languages (JS, Ruby and PHP) should be backwards compatiable (but will only detail a simple call graph). Feel free to fork or submit a PR to add further functionality to JS, Ruby and PHP.



## Setting Up PASTA

1. If you don't have it already, you will also need to install graphviz. Installation instructions can be found [here](https://graphviz.org/download/).
2. For now, the best method to install PASTA is to download the source files directly and running the script.

Additionally, depending on the language you want to parse, you may need to install additional dependencies:
- JavaScript: [Acorn](https://www.npmjs.com/package/acorn)
- Ruby: [Parser](https://github.com/whitequark/parser)
- PHP: [PHP-Parser](https://github.com/nikic/PHP-Parser)
- Python: No extra dependencies needed


## Using PASTA

To generate a DOT file, run something like:

```bash
pasta mypythonfile.py
```

You can specify multiple files or import directories:

```bash
pasta project/directory/source_a.py project/directory/source_b.py
```

```bash
pasta project/directory/*.py
```


To pull out a subset of the graph, try something like:

```bash
pasta mypythonfile.py --target-function my_func --upstream-depth=1 --downstream-depth=1
```


The output will always generate an out.gv file (graphviz) and a default out.png file
To output to svg, dot or json:

```bash
pasta mypythonfile.py --output out.svg
```


There are a ton of command line options, to see them all, run:

```bash
pasta --help
```



## How PASTA Works

Pasta approximates the structure of projects in dynamic languages. It is *not possible* to generate a perfect callgraph for a dynamic language. 

Detailed algorithm:

1. Generate an AST of the source code
2. Recursively separate groups and nodes. Groups are files, modules, or classes. More precisely, groups are namespaces where functions live. Nodes are the functions themselves and the details inside functions like If/Else, Try/Except etc.
3. For all function nodes, identify function calls in those nodes.
4. For all nodes, identify in-scope variables. Attempt to connect those variables to specific nodes and groups. This is where there is some ambiguity in the algorithm because it is impossible to know the types of variables in dynamic languages. So, instead, heuristics must be used.
5. For all calls in all nodes, attempt to find a match from the in-scope variables. This will be an edge.
6. For all other details inside of function Nodes, find the links to sub-node branches for If/Else, Try/Except Logic etc.
7. If a definitive match from in-scope variables cannot be found, attempt to find a single match from all other groups and nodes.
8. Trim orphaned nodes and groups.
9. Output results.



## Known Limitations

Pasta is internally powered by ASTs. Most limitations stem from a token not being named what Pasta expects it to be named.

* All functions without definitions are skipped. This most often happens when a file is not included.
* Functions with identical names in different namespaces are (loudly) skipped. E.g. If you have two classes with identically named methods, Pasta cannot distinguish between these and skips them.
* Imported functions from outside your project directory (including from standard libraries) which share names with your defined functions may not be handled correctly. Instead, when you call the imported function, Pasta will link to your local functions. For example, if you have a function `search()` and call, `import searcher; searcher.search()`, Pasta may link (incorrectly) to your defined function.
* Anonymous or generated functions are skipped. This includes lambdas and factories.
* If a function is renamed, either explicitly or by being passed around as a parameter, it will be skipped.



