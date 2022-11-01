import ast
import logging
import os
import inspect

from .model import (OWNER_CONST, GROUP_TYPE, Group, Node, Call, Variable,
                    BaseLanguage, djoin)


def get_call_from_func_element(func, parent):
    """
    Given a python ast that represents a function call, clear and create our
    generic Call object. Some children have no chance at resolution (e.g. array[2](param))
    so we return nothing instead.

    :param func ast:
    :rtype: Call|None
    """

    
    assert type(func) in (ast.Attribute, ast.Name, ast.Subscript, ast.Call)
    grouptoken = parent.token
    if type(func) == ast.Attribute:
        owner_token = []
        val = func.value
        while True:
            try:
                owner_token.append(getattr(val, 'attr', val.id))

            except AttributeError:
                pass
            val = getattr(val, 'value', None)
            if not val:
                break
        if owner_token:
            owner_token = djoin(*reversed(owner_token))
            if owner_token == grouptoken:
                owner_token = None # the codebase doesn't like when you self ref functions from the source file.
        else:
            owner_token = OWNER_CONST.UNKNOWN_VAR
        return Call(token=func.attr, line_number=func.lineno, owner_token=owner_token)
    if type(func) == ast.Name:
        return Call(token=func.id, line_number=func.lineno)
    if type(func) in (ast.Subscript, ast.Call):
        return None


def make_children(lines, parent):
    """
    Given a list of lines, find all children in this list.

    :param lines list[ast]:
    :rtype: list[Call]
    """

    children = []
    for tree in lines:
        for element in ast.walk(tree):
            if type(element) != ast.Call:
                continue
            call = get_call_from_func_element(element.func, parent)
            if call:
                children.append(call)
    return children


def process_assign(element, parent):
    """
    Given an element from the ast which is an assignment statement, return a
    Variable that points_to the type of object being assigned. For now, the
    points_to is a string but that is resolved later.

    :param element ast:
    :rtype: Variable
    """

    if type(element.value) != ast.Call:
        return []
    call = get_call_from_func_element(element.value.func, parent)
    if not call:
        return []

    ret = []
    for target in element.targets:
        if type(target) != ast.Name:
            continue
        token = target.id
        ret.append(Variable(token, call, element.lineno))
    return ret


def process_import(element):
    """
    Given an element from the ast which is an import statement, return a
    Variable that points_to the module being imported. For now, the
    points_to is a string but that is resolved later.

    :param element ast:
    :rtype: Variable
    """
    ret = []

    for single_import in element.names:
        #print("import:  ", single_import)

        assert isinstance(single_import, ast.alias)
        token = single_import.asname or single_import.name
        rhs = single_import.name
        #print('token: ', token)
        #print('rhs: ', rhs)

        if hasattr(element, 'module') and element.module:
            rhs = djoin(element.module, rhs)
            #print('module: ', rhs)
        ret.append(Variable(token, points_to=rhs, line_number=element.lineno))
    return ret

def make_arguments(arguments):

    args_obj_list = arguments.args
    arg_name_list = []

    for arg in args_obj_list:
        
        if arg.annotation != None:
            #print('arg: ', arg.arg, ' has annotation: ', arg.annotation.id)
            x = 1
        
        arg_name_list.append(arg.arg)

    return arg_name_list
            
        
def make_local_variables(lines, parent):
    """
    Given an ast of all the lines in a function, generate a list of
    variables in that function. Variables are tokens and what they link to.
    In this case, what it links to is just a string. However, that is resolved
    later.

    :param lines list[ast]:
    :param parent Group:
    :rtype: list[Variable]
    """
    variables = []

    #print('ABOUT TO CREATE VARIABLES')
    line_types = []
    #for ast in lines:
    #    if ast.targets not in line_types:
            #print(ast.targets[0].id)
    #        line_types.append(ast.targets)

    #print('Line Types: ',line_types)



    for tree in lines:
        for element in ast.walk(tree):
            if type(element) == ast.Assign:
                variables += process_assign(element, parent)
            if type(element) in (ast.Import, ast.ImportFrom):
                variables += process_import(element)
    if parent.group_type == GROUP_TYPE.CLASS:
        variables.append(Variable('self', parent, lines[0].lineno))

    #print('This is the list of vars: ', variables)
    variables = list(filter(None, variables))

    #print('This is the list Filtered: ', variables)
    return variables


def get_inherits(tree):
    """
    Get what superclasses this class inherits
    This handles exact names like 'MyClass' but skips things like 'cls' and 'mod.MyClass'
    Resolving those would be difficult
    :param tree ast:
    :rtype: list[str]
    """
    return [base.id for base in tree.bases if type(base) == ast.Name]


class Python(BaseLanguage):
    @staticmethod
    def assert_dependencies():
        pass

    @staticmethod
    def get_tree(filename, _):
        """
        Get the entire AST for this file

        :param filename str:
        :rtype: ast
        """
        try:
            with open(filename) as f:
                raw = f.read()
        except ValueError:
            with open(filename, encoding='UTF-8') as f:
                raw = f.read()
        return ast.parse(raw)

    @staticmethod
    def separate_namespaces(tree):
        """
        Given an AST, recursively separate that AST into lists of ASTs for the
        subgroups, nodes, and body. This is an intermediate step to allow for
        cleaner processing downstream

        :param tree ast:
        :returns: tuple of group, node, and body trees. These are processed
                  downstream into real Groups and Nodes.
        :rtype: (list[ast], list[ast], list[ast])
        """
        groups = [] # classes
        nodes = [] # functions and async functions
        body = [] # everything else
        ifcons = [] # look for if condition logic........ this is new

        for el in tree.body:
            #print('el is type: ', type(el))
            if type(el) in (ast.FunctionDef, ast.AsyncFunctionDef):
                print('function name: ',el.name)
                nodes.append(el)
                #Python.separate_namespaces(el)
                #groups += tup[0]
                #nodes += tup[1]
                #body += tup[2]
                #ifcons += tup[3]
            elif type(el) == ast.ClassDef:
                groups.append(el)
                #Python.separate_namespaces(el)
                #groups += tup[0]
                #nodes += tup[1]
                #body += tup[2]
                #ifcons += tup[3]
            elif type(el) == ast.If:
                ifcons.append(el)
                #Python.separate_namespaces(el)
                #groups += tup[0]
                #nodes += tup[1]
                #body += tup[2]
                #ifcons += tup[3]
            elif getattr(el, 'body', None):
                tup = Python.separate_namespaces(el)
                print('we are gonna dig deeper!') # this never runs with our code...
                groups += tup[0]
                nodes += tup[1]
                body += tup[2]
                ifcons += tup[3]
            else:
                body.append(el)
        
        print('if conditions found... ', ifcons)
        return groups, nodes, body, ifcons

    @staticmethod
    def make_nodes(tree, parent):
        """
        Given an ast of all the lines in a function, create the node along with the
        children and variables internal to it.

        :param tree ast:
        :param parent Group:
        :rtype: list[Node]
        """

        asttype = {
            'Assign': 'targets',
            'Expr': 'value',
            'ImportFrom': 'module',
            'Import': 'names',
            'Try': 'body',
            'If': 'test',
            'Return': 'value',
            'Name': 'id'
        }

        
        #print('TREE NAME: ', tree.name)
        for item in tree.body:
            # determine what type of ast object the item is
            itemType = type(item).__name__
            
            # if it is a try or if block then more logic needs to be done and new nodes need to be created
            if itemType == 'Try' or itemType == 'If':
                #print(item)
                x = 1
            
            elif itemType == 'Assign':
                targetType = type(item.targets).__name__
                #print('targetType: ', targetType)
                assignVars = []
                for vars in item.targets:

                    if type(vars).__name__ == 'Name':
                        #print('targets: ', vars.id) 
                        #print('value: ', item.value)
                        x = 1
                    elif type(vars).__name__ == 'Attribute':
                        #print('attribute!!!!!!!')
                        #print(vars.value.func.value.id)
                        x = 1
                    elif type(vars).__name__ == 'Tuple':
                        #print('TUPLE!!!!!!!!!!!')
                        #print('targets: ', vars.elts)
                        x = 1


        token = tree.name

        

        #arguments = make_arguments(tree.args)
        line_number = tree.lineno
        children = make_children(tree.body, parent)
        variables = make_local_variables(tree.body, parent)
        is_constructor = False

        if parent.group_type == GROUP_TYPE.CLASS and token in ['__init__', '__new__']:
            is_constructor = True

        import_tokens = []
        if parent.group_type == GROUP_TYPE.FILE:
            import_tokens = [djoin(parent.token, token)]


        if token == 'autoStartEnd':
            print('adding nodes for autostartend!!!')
            print('children: ', children)
            print('variables: ', variables)
            print('parent: ', parent)


        return [Node(token, children, variables, parent, import_tokens=import_tokens,
                     line_number=line_number, is_constructor=is_constructor)]

    @staticmethod
    def make_root_node(lines, parent):
        """
        The "root_node" is an implict node of lines which are executed in the global
        scope on the file itself and not otherwise part of any function.

        :param lines list[ast]:
        :param parent Group:
        :rtype: Node
        """
        token = "(global)"
        line_number = 0
        children = make_children(lines, parent)
        variables = make_local_variables(lines, parent)
        return Node(token, children, variables, parent, line_number=line_number)

    @staticmethod
    def make_class_group(tree, parent):
        """
        Given an AST for the subgroup (a class), generate that subgroup.
        In this function, we will also need to generate all of the nodes internal
        to the group.

        :param tree ast:
        :param parent Group:
        :rtype: Group
        """
        assert type(tree) == ast.ClassDef
        subgroup_trees, node_trees, body_trees = Python.separate_namespaces(tree)

        group_type = GROUP_TYPE.CLASS
        token = tree.name
        display_name = 'Class'
        line_number = tree.lineno

        import_tokens = [djoin(parent.token, token)]
        inherits = get_inherits(tree)

        class_group = Group(token, group_type, display_name, import_tokens=import_tokens,
                            inherits=inherits, line_number=line_number, parent=parent)

        for node_tree in node_trees:
            class_group.add_node(Python.make_nodes(node_tree, parent=class_group)[0])

        for subgroup_tree in subgroup_trees:
            logging.warning("pasta does not support nested classes. Skipping %r in %r.",
                            subgroup_tree.name, parent.token)
        return class_group

    @staticmethod
    def file_import_tokens(filename):
        """
        Returns the token(s) we would use if importing this file from another.

        :param filename str:
        :rtype: list[str]
        """
        return [os.path.split(filename)[-1].rsplit('.py', 1)[0]]
