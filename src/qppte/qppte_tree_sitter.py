import tree_sitter_python
from tree_sitter import Language, Parser, Query

PY_LANGUAGE = Language(tree_sitter_python.language())
PYTHON_PARSER = Parser(PY_LANGUAGE)
HIGHLIGHTER_QUERY = Query(
    PY_LANGUAGE,
    """
        (function_definition
          name: (identifier) @function_definition)

        (function_definition (identifier) @special_function (#any-of? @special_function 
                                                                        "__init__" "__new__" "__setattr__" 
                                                                        "__delattr__" "__eq__" "__ne__" 
                                                                        "__str__" "__hash__" "__format__" 
                                                                        "__getattribute__" "__sizeof__" "__dir__" 
                                                                        "__repr__"))
        ("." (identifier) @special_function (#any-of? @special_function 
                                                        "__init__" "__new__" "__setattr__" "__delattr__" "__eq__" 
                                                        "__ne__" "__str__" "__hash__" "__format__" "__getattribute__" 
                                                        "__sizeof__" "__dir__" "__repr__"))

        (type) @type

        (class_definition
          name: (identifier) @class_definition_name)

        (call (identifier) @function_call)
        (decorator "@" (identifier)) @decorator 
        (decorator "@" (call (identifier) @decorator))  
        (decorator ("@" @decorator))

        (string_start) @string
        (string_content) @string
        (string_end) @string

        ["def" "return" "if" "else" "class" "assert" "async" "await" "break" "continue" "del" "elif" 
         "else" "except" "finally" "for" "global" "lambda" "pass" "raise" "nonlocal" "return" "try" 
         "while" "yield" "as" "with" "import" "from" "match" "case" "in"] @keyword

        (true) @keyword
        (false) @keyword

        (integer) @number
        (float) @number

        (keyword_argument (identifier) @keyword_argument) 

        ((identifier) @self (#eq? @self "self"))

        (comment) @line_comment

        (function_definition (block . (expression_statement (string) @docstring)))
        (class_definition (block . (expression_statement (string) @docstring)))
        (module . (expression_statement (string) @docstring))
    """,
)
