import os
import re
import sys


class JackTokenizer:
    KEYWORDS = {
        'class', 'constructor', 'function', 'method', 'field', 'static',
        'var', 'int', 'char', 'boolean', 'void', 'true', 'false', 'null',
        'this', 'let', 'do', 'if', 'else', 'while', 'return'
    }
    SYMBOLS = {
        '{', '}', '(', ')', '[', ']', '.', ',', ';', '+', '-', '*', '/',
        '&', '|', '<', '>', '=', '~'
    }

    def __init__(self, input_file):
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        self.tokens = self._tokenize(content)
        self.cursor = -1
        self.current_token = None

    def _tokenize(self, content):
        content = re.sub(r'/\*[\s\S]*?\*/', ' ', content)
        content = re.sub(r'//.*', ' ', content)
        token_pattern = re.compile(
            r'\"[^\n\"]*\"|[a-zA-Z_]\w*|\d+|[\{\}\(\)\[\]\.,;\+\-\*/&\|<>=~]'
        )
        return token_pattern.findall(content)

    def has_more_tokens(self):
        return self.cursor + 1 < len(self.tokens)

    def advance(self):
        if self.has_more_tokens():
            self.cursor += 1
            self.current_token = self.tokens[self.cursor]

    def peek(self):
        if self.has_more_tokens():
            return self.tokens[self.cursor + 1]
        return None

    def token_type(self):
        if self.current_token in self.KEYWORDS:
            return 'KEYWORD'
        elif self.current_token in self.SYMBOLS:
            return 'SYMBOL'
        elif self.current_token.isdigit():
            return 'INT_CONST'
        elif self.current_token.startswith('"') and self.current_token.endswith('"'):
            return 'STRING_CONST'
        else:
            return 'IDENTIFIER'

    def int_val(self):
        return int(self.current_token)

    def string_val(self):
        return self.current_token[1:-1]


class SymbolTable:
    def __init__(self):
        self.class_table = {}
        self.subroutine_table = {}
        self.indices = {
            'STATIC': 0,
            'FIELD': 0,
            'ARG': 0,
            'VAR': 0
        }

    def start_subroutine(self):
        self.subroutine_table.clear()
        self.indices['ARG'] = 0
        self.indices['VAR'] = 0

    def define(self, name, var_type, kind):
        kind = kind.upper()
        index = self.indices[kind]
        self.indices[kind] += 1

        entry = (var_type, kind, index)
        if kind in ('STATIC', 'FIELD'):
            self.class_table[name] = entry
        elif kind in ('ARG', 'VAR'):
            self.subroutine_table[name] = entry

    def var_count(self, kind):
        return self.indices[kind.upper()]

    def kind_of(self, name):
        if name in self.subroutine_table:
            return self.subroutine_table[name][1]
        if name in self.class_table:
            return self.class_table[name][1]
        return 'NONE'

    def type_of(self, name):
        if name in self.subroutine_table:
            return self.subroutine_table[name][0]
        if name in self.class_table:
            return self.class_table[name][0]
        return None

    def index_of(self, name):
        if name in self.subroutine_table:
            return self.subroutine_table[name][2]
        if name in self.class_table:
            return self.class_table[name][2]
        return None


class VMWriter:
    def __init__(self, output_file):
        self.out = open(output_file, 'w', encoding='utf-8')

    def write_push(self, segment, index):
        self.out.write(f"push {segment.lower()} {index}\n")

    def write_pop(self, segment, index):
        self.out.write(f"pop {segment.lower()} {index}\n")

    def write_arithmetic(self, command):
        self.out.write(f"{command.lower()}\n")

    def write_label(self, label):
        self.out.write(f"label {label}\n")

    def write_goto(self, label):
        self.out.write(f"goto {label}\n")

    def write_if(self, label):
        self.out.write(f"if-goto {label}\n")

    def write_call(self, name, n_args):
        self.out.write(f"call {name} {n_args}\n")

    def write_function(self, name, n_locals):
        self.out.write(f"function {name} {n_locals}\n")

    def write_return(self):
        self.out.write("return\n")

    def close(self):
        self.out.close()


class CompilationEngine:
    OP_MAP = {
        '+': 'add',
        '-': 'sub',
        '&': 'and',
        '|': 'or',
        '<': 'lt',
        '>': 'gt',
        '=': 'eq'
    }

    UNARY_OP_MAP = {
        '-': 'neg',
        '~': 'not'
    }

    KIND_TO_SEGMENT = {
        'STATIC': 'static',
        'FIELD': 'this',
        'ARG': 'argument',
        'VAR': 'local'
    }

    def __init__(self, input_file, output_file):
        self.tokenizer = JackTokenizer(input_file)
        self.symbol_table = SymbolTable()
        self.vm_writer = VMWriter(output_file)
        self.class_name = ''
        self.label_counter = 0

        if self.tokenizer.has_more_tokens():
            self.tokenizer.advance()

    def _eat(self, expected=None):
        val = self.tokenizer.current_token
        if expected is not None and val != expected:
            raise SyntaxError(f"Expected '{expected}', got '{val}'")
        if self.tokenizer.has_more_tokens():
            self.tokenizer.advance()
        return val

    def _new_label(self, prefix):
        label = f"{self.class_name}_{prefix}_{self.label_counter}"
        self.label_counter += 1
        return label

    def compile_class(self):
        self._eat('class')
        self.class_name = self._eat()
        self._eat('{')

        while self.tokenizer.current_token in ('static', 'field'):
            self.compile_class_var_dec()

        while self.tokenizer.current_token in ('constructor', 'function', 'method'):
            self.compile_subroutine()

        self._eat('}')
        self.vm_writer.close()

    def compile_class_var_dec(self):
        kind = self._eat()
        var_type = self._eat()
        name = self._eat()
        self.symbol_table.define(name, var_type, kind)

        while self.tokenizer.current_token == ',':
            self._eat(',')
            name = self._eat()
            self.symbol_table.define(name, var_type, kind)

        self._eat(';')

    def compile_subroutine(self):
        self.symbol_table.start_subroutine()
        sub_type = self._eat()
        self._eat()  # return type
        sub_name = self._eat()

        if sub_type == 'method':
            self.symbol_table.define('this', self.class_name, 'ARG')

        self._eat('(')
        self.compile_parameter_list()
        self._eat(')')

        self.compile_subroutine_body(sub_type, sub_name)

    def compile_parameter_list(self):
        if self.tokenizer.current_token != ')':
            var_type = self._eat()
            name = self._eat()
            self.symbol_table.define(name, var_type, 'ARG')

            while self.tokenizer.current_token == ',':
                self._eat(',')
                var_type = self._eat()
                name = self._eat()
                self.symbol_table.define(name, var_type, 'ARG')

    def compile_subroutine_body(self, sub_type, sub_name):
        self._eat('{')
        while self.tokenizer.current_token == 'var':
            self.compile_var_dec()

        n_locals = self.symbol_table.var_count('VAR')
        self.vm_writer.write_function(f"{self.class_name}.{sub_name}", n_locals)

        if sub_type == 'constructor':
            n_fields = self.symbol_table.var_count('FIELD')
            self.vm_writer.write_push('constant', n_fields)
            self.vm_writer.write_call('Memory.alloc', 1)
            self.vm_writer.write_pop('pointer', 0)
        elif sub_type == 'method':
            self.vm_writer.write_push('argument', 0)
            self.vm_writer.write_pop('pointer', 0)

        self.compile_statements()
        self._eat('}')

    def compile_var_dec(self):
        self._eat('var')
        var_type = self._eat()
        name = self._eat()
        self.symbol_table.define(name, var_type, 'VAR')

        while self.tokenizer.current_token == ',':
            self._eat(',')
            name = self._eat()
            self.symbol_table.define(name, var_type, 'VAR')

        self._eat(';')

    def compile_statements(self):
        while self.tokenizer.current_token in ('let', 'if', 'while', 'do', 'return'):
            stmt = self.tokenizer.current_token
            if stmt == 'let':
                self.compile_let()
            elif stmt == 'if':
                self.compile_if()
            elif stmt == 'while':
                self.compile_while()
            elif stmt == 'do':
                self.compile_do()
            elif stmt == 'return':
                self.compile_return()

    def compile_let(self):
        self._eat('let')
        var_name = self._eat()
        kind = self.symbol_table.kind_of(var_name)
        segment = self.KIND_TO_SEGMENT[kind]
        index = self.symbol_table.index_of(var_name)

        is_array = False
        if self.tokenizer.current_token == '[':
            is_array = True
            self._eat('[')
            self.vm_writer.write_push(segment, index)
            self.compile_expression()
            self._eat(']')
            self.vm_writer.write_arithmetic('add')

        self._eat('=')
        self.compile_expression()
        self._eat(';')

        if is_array:
            self.vm_writer.write_pop('temp', 0)
            self.vm_writer.write_pop('pointer', 1)
            self.vm_writer.write_push('temp', 0)
            self.vm_writer.write_pop('that', 0)
        else:
            self.vm_writer.write_pop(segment, index)

    def compile_if(self):
        else_label = self._new_label('IF_ELSE')
        end_label = self._new_label('IF_END')

        self._eat('if')
        self._eat('(')
        self.compile_expression()
        self._eat(')')

        self.vm_writer.write_arithmetic('not')
        self.vm_writer.write_if(else_label)

        self._eat('{')
        self.compile_statements()
        self._eat('}')

        if self.tokenizer.current_token == 'else':
            self.vm_writer.write_goto(end_label)
            self.vm_writer.write_label(else_label)
            self._eat('else')
            self._eat('{')
            self.compile_statements()
            self._eat('}')
            self.vm_writer.write_label(end_label)
        else:
            self.vm_writer.write_label(else_label)

    def compile_while(self):
        exp_label = self._new_label('WHILE_EXP')
        end_label = self._new_label('WHILE_END')

        self.vm_writer.write_label(exp_label)
        self._eat('while')
        self._eat('(')
        self.compile_expression()
        self._eat(')')

        self.vm_writer.write_arithmetic('not')
        self.vm_writer.write_if(end_label)

        self._eat('{')
        self.compile_statements()
        self._eat('}')

        self.vm_writer.write_goto(exp_label)
        self.vm_writer.write_label(end_label)

    def compile_do(self):
        self._eat('do')
        self._compile_subroutine_call()
        self._eat(';')
        self.vm_writer.write_pop('temp', 0)

    def compile_return(self):
        self._eat('return')
        if self.tokenizer.current_token != ';':
            self.compile_expression()
        else:
            self.vm_writer.write_push('constant', 0)
        self._eat(';')
        self.vm_writer.write_return()

    def compile_expression(self):
        self.compile_term()
        while self.tokenizer.current_token in ('+', '-', '*', '/', '&', '|', '<', '>', '='):
            op = self._eat()
            self.compile_term()
            if op == '*':
                self.vm_writer.write_call('Math.multiply', 2)
            elif op == '/':
                self.vm_writer.write_call('Math.divide', 2)
            else:
                self.vm_writer.write_arithmetic(self.OP_MAP[op])

    def compile_term(self):
        t_type = self.tokenizer.token_type()

        if t_type == 'INT_CONST':
            val = self.tokenizer.int_val()
            self._eat()
            self.vm_writer.write_push('constant', val)

        elif t_type == 'STRING_CONST':
            s = self.tokenizer.string_val()
            self._eat()
            self.vm_writer.write_push('constant', len(s))
            self.vm_writer.write_call('String.new', 1)
            for ch in s:
                self.vm_writer.write_push('constant', ord(ch))
                self.vm_writer.write_call('String.appendChar', 2)

        elif t_type == 'KEYWORD':
            kw = self._eat()
            if kw == 'true':
                self.vm_writer.write_push('constant', 0)
                self.vm_writer.write_arithmetic('not')
            elif kw in ('false', 'null'):
                self.vm_writer.write_push('constant', 0)
            elif kw == 'this':
                self.vm_writer.write_push('pointer', 0)

        elif self.tokenizer.current_token == '(':
            self._eat('(')
            self.compile_expression()
            self._eat(')')

        elif self.tokenizer.current_token in ('-', '~'):
            op = self._eat()
            self.compile_term()
            self.vm_writer.write_arithmetic(self.UNARY_OP_MAP[op])

        elif t_type == 'IDENTIFIER':
            next_tok = self.tokenizer.peek()
            if next_tok == '[':
                var_name = self._eat()
                kind = self.symbol_table.kind_of(var_name)
                self.vm_writer.write_push(
                    self.KIND_TO_SEGMENT[kind],
                    self.symbol_table.index_of(var_name)
                )
                self._eat('[')
                self.compile_expression()
                self._eat(']')
                self.vm_writer.write_arithmetic('add')
                self.vm_writer.write_pop('pointer', 1)
                self.vm_writer.write_push('that', 0)
            elif next_tok in ('(', '.'):
                self._compile_subroutine_call()
            else:
                var_name = self._eat()
                kind = self.symbol_table.kind_of(var_name)
                self.vm_writer.write_push(
                    self.KIND_TO_SEGMENT[kind],
                    self.symbol_table.index_of(var_name)
                )

    def _compile_subroutine_call(self):
        name1 = self._eat()
        n_args = 0

        if self.tokenizer.current_token == '.':
            self._eat('.')
            name2 = self._eat()
            kind = self.symbol_table.kind_of(name1)
            if kind != 'NONE':
                obj_type = self.symbol_table.type_of(name1)
                self.vm_writer.write_push(
                    self.KIND_TO_SEGMENT[kind],
                    self.symbol_table.index_of(name1)
                )
                full_name = f"{obj_type}.{name2}"
                n_args = 1
            else:
                full_name = f"{name1}.{name2}"
        else:
            self.vm_writer.write_push('pointer', 0)
            full_name = f"{self.class_name}.{name1}"
            n_args = 1

        self._eat('(')
        n_args += self.compile_expression_list()
        self._eat(')')
        self.vm_writer.write_call(full_name, n_args)

    def compile_expression_list(self):
        count = 0
        if self.tokenizer.current_token != ')':
            self.compile_expression()
            count += 1
            while self.tokenizer.current_token == ',':
                self._eat(',')
                self.compile_expression()
                count += 1
        return count


def compile_file(jack_path):
    vm_path = os.path.splitext(jack_path)[0] + '.vm'
    print(f"Compiling {jack_path} -> {vm_path}")
    engine = CompilationEngine(jack_path, vm_path)
    engine.compile_class()


def main():
    if len(sys.argv) != 2:
        print("Usage: python JackCompiler.py <file.jack | directory>")
        sys.exit(1)

    target = sys.argv[1]
    if os.path.isfile(target) and target.endswith('.jack'):
        compile_file(target)
    elif os.path.isdir(target):
        for filename in os.listdir(target):
            if filename.endswith('.jack'):
                compile_file(os.path.join(target, filename))
    else:
        print("Error: Please provide a valid .jack file or directory.")
        sys.exit(1)


if __name__ == '__main__':
    main()