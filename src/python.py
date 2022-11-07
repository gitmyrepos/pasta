import ast
import logging
import os
import inspect

from .model import (OWNER_CONST, GROUP_TYPE, Group, Node, Call, Variable, IfNode,
                    BaseLanguage, djoin)


def get_call_from_func_element(func, parent):
    """
    Given a python ast that represents a function call, clear and create our
    generic Call object. Some calls have no chance at resolution (e.g. array[2](param))
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


def make_calls(lines, parent):
    """
    Given a list of lines, find all calls in this list.

    :param lines list[ast]:
    :rtype: list[Call]
    """
    #print('about to make calls elements, ', lines)
    calls = []
    for tree in lines:
        for element in ast.iter_child_nodes(tree):
            #print('call element?: ', element)
            if type(element) == ast.Call:
                call = get_call_from_func_element(element.func, parent)
                if call:
                    calls.append(call)

            
               
    return calls


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

def process_if(element):
    ret = []
    print('processing if node, ', element)
    ret.append(Variable())

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
        for element in ast.iter_child_nodes(tree):
            if type(element) == ast.Assign:
                variables += process_assign(element, parent)
            if type(element) in (ast.Import, ast.ImportFrom):
                variables += process_import(element)
            #if type(element) == ast.If:
            #    variables += process_if(element)
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

        #    if isinstance(code_ast, ast.AST):
        #    print('codeAST: ', code_ast)
        #    # This looks like if the code_ast is indeed just a single node then it will extract its data fields/attributes
        #    #print(code_ast, ', IS an AST object!')
        #    node = {to_camelcase(k): transform_ast(getattr(code_ast, k)) for k in code_ast._fields}
        #    node['node_type'] = to_camelcase(code_ast.__class__.__name__)
        #    #print(type(node))
        #    return node


        groups = [] # classes and functions with split logic
        nodes = [] # simple functions and async functions
        body = [] # everything else

        for el in tree.body:
            #print('el is type: ', type(el))
            if type(el) in (ast.FunctionDef, ast.AsyncFunctionDef):
                #print('func type:  ', type(el))
                nodes.append(el)
                #tup = Python.separate_namespaces(el)
                #groups += tup[0]
                #nodes += tup[1]
                #body += tup[2]
              
            elif type(el) == ast.ClassDef:
                groups.append(el)
                #tup = Python.separate_namespaces(el)
                #groups += tup[0]
                #nodes += tup[1]
                #body += tup[2]
                
            elif getattr(el, 'body', None):
                tup = Python.separate_namespaces(el)
                print('we are gonna dig deeper!') # this never runs with our code...
                groups += tup[0]
                nodes += tup[1]
                body += tup[2]
            else:
                body.append(el)
        
        #print('if conditions found... ', ifcons)
        return groups, nodes, body

    @staticmethod
    def eval_funcs(funcs):
        print('about to eval funcs')
        simple_funcs = funcs
        complex_funcs = []

        for func in funcs:
            for el in ast.iter_child_nodes(func):
                if type(el) == ast.If:
                    complex_funcs.append(func)
                    simple_funcs.remove(func)
                    break
            
        return simple_funcs, complex_funcs

    @staticmethod
    def make_nodes(tree, parent, root_name=None, root_num=0, array_num=0, uid=None):
        """
        Given an ast of all the lines in a function, create the node along with the
        calls and variables internal to it.

        :param tree ast:
        :param parent Group:
        :rtype: list[Node]
        """

        #nodeName = tree.name
        #print('the token for normal nodes is:   ', type(token))
        #arguments = make_arguments(tree.args)
        #line_number = tree.lineno

         # basically I need to find index of ifs and subnodes (statements between ifs)
        # to create a subnode I need to know what vars are in body in index which means I should only accept body elements and calls from
        # that section from start or If to next if or finish....
        
        # the outter function will determine the head function 
        # determine substituted body...

        # first check if we need to change anything at all if there even exists an IF statement
        # this assumes there is no if, if we find one then we change body to appropriate variable

        if root_name == None:
            root_name = tree.name

        if root_name == 'complianceConfirmation':
            print('COMPLIANCE FOUND!!!!!!!')
        #print('root name: ', root_name)

        # assume no arguments are needed unless an ast.arguments node is found.
        arguments = None
        
        # This first checks what sort of tree is given if it is a list or ast.functionDef
        # and puts all child elements into a list if necessary (excluding arguments)
        # if arguments are found it sets the arguments var
        ungrouped_nodes = []
        if type(tree) == ast.FunctionDef:
            for el in ast.iter_child_nodes(tree):
                if type(el) == ast.arguments:
                    arguments = el
                else:
                    ungrouped_nodes.append(el)

        # if the tree given is a list (body of previous function/if element) then just use the list
        if type(tree) == list:
            ungrouped_nodes = tree

        # This looks into the list of nodes and looks for ifs and separates out groups of nodes
        group = []
        groups = []
        for el in ungrouped_nodes:
            if type(el) == ast.If:
                # add previous group to groups
                if group != []:
                    groups.append(group)
                # add new group for ast.If
                groups.append([el])
                # reset group
                group = []
            else:
                # if the element is not an ast.If then add it to the current group
                group.append(el)

        # if an ast.If was last in the ungroup_nodes then group would = [] which we don't need
        # however if there remains any other elements the last group we need to add it to groups
        if group != []:
            groups.append(group)


        # Sanity check to see a list of groups in sub_bodies if the list is 1 then it's a normal node with no IF logic
        # if the length of sub_bodies is more than 1 there should be at least 1 IfNode which requires further logic
        #print('this is length of groups: ', len(groups))
        if root_name == 'complianceConfirmation':
            print('root num: ', root_num)
        # Now we analyize each sub_group of nodes and create new nodes out of them either normal function/body nodes or IfNodes
        nodes_to_return = []
        for group in groups:
            # if the group is a normal node (not an ast.If)
            
            if type(group[0]) != ast.If:
                # assign token (token = nodeID)
                # assign nodeName (display name on map)
                print('root/array: ', root_num, '/', array_num)
                
                if root_num == 0 and array_num == 0:
                    token = root_name
                    nodeName = root_name

                else:
                    token = root_name + 'R' + str(root_num) + 'A' + str(array_num)
                    nodeName = root_name
                    
                # assign line number
                line_number = group[0].lineno
                # assign calls for this node
                calls = make_calls(group, parent)
                # assign variables for this node
                variables = make_local_variables(group, parent)
                # assign import tokens
                import_tokens = []
                if parent.group_type == GROUP_TYPE.FILE:
                    import_tokens = [djoin(parent.token, token)]
                # assign is_constructor
                is_constructor = False
                if parent.group_type == GROUP_TYPE.CLASS and token in ['__init__', '__new__']:
                    is_constructor = True
                # if sub_bodies len is greater than index then assign if as tree.name_if_index(of if)
                ifNode = None
                # since the current index is a normal node and if the current index is not the last in the sub_bodies list then the next index must be an IF node
                if groups.index(group) + 1 < len(groups):
                    ifNode = "node_" + os.urandom(4).hex()

                # now create this node and add it to the list of nodes to return.
                if root_name == 'complianceConfirmation':
               
                    print('FUNC NODE: ', token)
                    print('vars: ', variables)
                    print('calls: ', calls)
                    print('my if node: ', ifNode)
                nodes_to_return.append(Node(token, nodeName, calls, variables, parent, import_tokens=import_tokens, line_number=line_number, is_constructor=is_constructor, args=arguments, ifNode=ifNode, uid=uid))
                uid = ifNode

            if type(group[0]) == ast.If:
                # create an if node using tree.name (function name) + index as token
                #print('this should be an ast.IF: ', group)
                # create token
                token = root_name + 'R' + str(root_num) + 'A' + str(array_num)
                # create name
                name = 'IF'
                # create condition
                lineno = group[0].test.lineno
                condition = Python.make_condition_str(group[0].test)
                if type(condition) == ast.Compare:
                    print('compare: ', condition.left)
                    print('ops: ', condition.ops)
                    print('comparators: ', condition.comparators)
                # create ifTrueID
                ifTrueID = "node_" + os.urandom(4).hex()
                trueNodes = Python.make_nodes(group[0].body, parent, root_name=root_name, root_num=(root_num+1), uid=ifTrueID)
                nodes_to_return += trueNodes
                # check if ifFalse exists
                ifFalseID = None
                if group[0].orelse:
                    ifFalseID = "node_" + os.urandom(4).hex()
                    falseNodes = Python.make_nodes(group[0].orelse, parent, root_name=root_name, root_num=(root_num+100), uid=ifFalseID)
                    nodes_to_return += falseNodes
        
                # if this IfNode in list sub_bodies is not the last in the list then add cont id and connect to next item
                ifContID = None
                #print('group len: ', len(group))
                if groups.index(group) + 1 < len(groups):
                    ifContID = "node_" + os.urandom(4).hex()
                    
                nodes_to_return.append(IfNode(token, name, condition, ifTrueID, parent, ifFalseID=ifFalseID, ifContID=ifContID, uid=uid, lineno=lineno))
                uid = ifContID
            array_num += 1
        # last sanity check to see what nodes we will return to caller
        #print('nodes to return: ', nodes_to_return)
        return nodes_to_return

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
        nodeName = token
        line_number = 0
        calls = make_calls(lines, parent)
        variables = make_local_variables(lines, parent)
        return Node(token, nodeName, calls, variables, parent, line_number=line_number)

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

        if type(tree) == ast.ClassDef:
    
            # split up class node into body, nodes (functions) and subclasses
            subgroup_trees, node_trees, body_trees = Python.separate_namespaces(tree)

            # set group info
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

    @staticmethod
    def make_condition_str(condition):
        print('condition to parse: ', condition)
        return_str = ''
        if type(condition) == ast.Compare:
            compare = condition.left
            ops = condition.ops
            comparators = condition.comparators

            if type(compare) == ast.Call:
                if 'ast' in str(compare.func):
                    print('compare what???? ', compare.func)
                    if type(compare.func) == ast.Attribute:
                        print('compare attr: ', compare.func.attr)
                        return_str += str(compare.func.attr)
                    if type(compare.func) == ast.Name:
                        print('name: ', compare.func.id)
                        return_str += str(compare.func.id)

            if type(compare) == ast.Name:
                return_str += str(compare.id)

            if len(ops) == 1:
                if type(ops[0]) == ast.Eq:
                    return_str += ' =='
                if type(ops[0]) == ast.NotEq:
                    return_str += ' !='
                if type(ops[0]) == ast.Lt:
                    return_str += ' <'
                if type(ops[0]) == ast.LtE:
                    return_str += ' <='
                if type(ops[0]) == ast.Gt:
                    return_str += ' >'
                if type(ops[0]) == ast.GtE:
                    return_str += ' >='
                if type(ops[0]) == ast.Is:
                    return_str += ' IS'
                if type(ops[0]) == ast.IsNot:
                    return_str += ' IS NOT'
                if type(ops[0]) == ast.In:
                    return_str += ' IN'
                if type(ops[0]) == ast.NotIn:
                    return_str += ' NOT IN'

            else:
                print('ops is too complicated!!!')

            if len(comparators) == 1:
                if type(comparators[0]) == ast.Constant or type(comparators[0]) == ast.Attribute:
                    if 'ast' in str(comparators[0].value):
                        return_str += ' ' + str(comparators[0].value.value.id)
                    else:
                        return_str += ' ' + str(comparators[0].value)
                
            else:
                print('comparators is too complicated!!!')
            
            return return_str

        elif type(condition) == ast.Call:
            if 'ast' in str(condition.func):
                print('compare what???? ', condition.func)
                if type(condition.func) == ast.Attribute:
                    print('compare attr: ', condition.func.attr)
                    return_str += str(condition.func.attr)
                if type(condition.func) == ast.Name:
                    print('name: ', condition.func.id)
                    return_str += str(condition.func.id)
            return return_str

        elif type(condition) == ast.BoolOp:
            print('found a bool: ', condition.lineno)
            print('a compare in a bool: ', Python.make_condition_str(condition.values[0]))
            
            op = condition.op

            if 'ast.Or' in str(op):
              
                op = 'OR'
            elif 'ast.And' in str(op):
    
                op = 'AND'

            vlen = len(condition.values)
            i = 1
            for v in condition.values:
                if i != 1:
                    return_str += ' '
                return_str += Python.make_condition_str(v)
                if i != vlen:
                    return_str += ' ' + str(op)
                i += 1
            return return_str
        
        elif type(condition) == ast.UnaryOp:
            op = condition.op
            if isinstance(op, ast.Not):
                op = 'NOT'
            elif isinstance(op, ast.UAdd):
                op = '+'
            elif isinstance(op, ast.USub):
                op = '-'
            elif isinstance(op, ast.Invert):
                op = '~'

            
            operand = condition.operand
            
            if isinstance(operand, ast.Name):
                operand = operand.id

            return str(op) + ' ' + str(operand)

        elif type(condition) == ast.Name:
            return condition.id
            
        else:
            return 'IDK'