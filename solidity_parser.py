#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Author: Sphantix
# Mail: sphantix@gmail.cn
# created time: Tue 12 Jun 2018 09:30:45 AM CST
import re
import sys
import json


class ParseErrorException(Exception):
    def __init__(self, err='Parse Error!'):
        Exception.__init__(self, err)


class Block(object):
    def __init__(self, key_word, handler):
        self.key_word = key_word
        self.handler = handler


class Stack(object):
    def __init__(self):
        self.items = []

    def is_empty(self):
        return self.items == []

    def peek(self):
        return self.items[len(self.items) - 1]

    def depth(self):
        return len(self.items)

    def push(self, item):
        self.items.append(item)

    def pop(self):
        return self.items.pop()


class SolidityParser(object):
    def __init__(self, content, EF):
        self.content = content
        self.EF = EF           #End Flag
        self.stack = Stack()

        self.reserve_words = ["pragma", "library", "contract", "is",
                              "function", "event", "emit", "modifier",
                              "return", "public", "private", "const",
                              "external", "internal", "payable", "assert",
                              "require", "throw", "import", "as",
                              "indexed", "pure", "view", "memory",
                              "storage", "calldata"]
        self.limiter = ["(", ")", "{", "}", "[", "]"]
        self.operations = ["==", "!=", "=", "+",
                           "-", "*", "/", "**"]
        self.types = ['address', 'bool', 'string', 'var', 'int', 'int8',
                      'int16', 'int24', 'int32', 'int40', 'int48', 'int56',
                      'int64', 'int72', 'int80', 'int88', 'int96', 'int104',
                      'int112', 'int120', 'int128', 'int136', 'int144', 'int152',
                      'int160', 'int168', 'int176', 'int184', 'int192', 'int200',
                      'int208', 'int216', 'int224', 'int232', 'int240', 'int248',
                      'int256', 'uint', 'uint8', 'uint16', 'uint24', 'uint32',
                      'uint40', 'uint48', 'uint56', 'uint64', 'uint72', 'uint80',
                      'uint88', 'uint96', 'uint104', 'uint112', 'uint120',
                      'uint128', 'uint136', 'uint144', 'uint152', 'uint160',
                      'uint168', 'uint176', 'uint184', 'uint192', 'uint200',
                      'uint208', 'uint216', 'uint224', 'uint232', 'uint240',
                      'uint248', 'uint256','byte', 'bytes', 'bytes1', 'bytes2',
                      'bytes3', 'bytes4', 'bytes5', 'bytes6', 'bytes7', 'bytes8',
                      'bytes9', 'bytes10', 'bytes11', 'bytes12', 'bytes13',
                      'bytes14', 'bytes15', 'bytes16', 'bytes17', 'bytes18',
                      'bytes19', 'bytes20', 'bytes21', 'bytes22', 'bytes23',
                      'bytes24', 'bytes25', 'bytes26', 'bytes27', 'bytes28',
                      'bytes29', 'bytes30', 'bytes31', 'bytes32']
        self.blocks = [Block("pragma", self.handle_pragma),
                       Block("import", self.handle_import),
                       Block("library", self.handle_library),
                       Block("interface", self.handle_interface),
                       Block("contract", self.handle_contract)]

    def is_limiter(self, content):
        if content in self.limiter:
            return True

        return False

    def is_terminator(self, content):
        if content == ' ':
            return True
        if content == ';':
            return True
        if content == ',':
            return True
        if self.is_limiter(content):
            return True

        return False

    def handle_parameters(self, pos):
        result = []
        type = None
        modifiers = []
        name = None

        while True:
            word, pos = self.get_one_word(pos)
            if word == ")":
                if self.stack.peek() != "(":
                    raise ParseErrorException("Parse Error!")
                else:
                    self.stack.pop()
                    break
            elif word == ",":
                continue
            elif word == "[":
                self.stack.push("[")
                modifiers.append("array")
                continue
            elif word == "]":
                if self.stack.peek() != "[":
                    raise ParseErrorException("Parse Error!")
                else:
                    self.stack.pop()
                    continue
            elif word in self.types:
                type = word
                modifiers = []
            elif word in self.reserve_words:
                modifiers.append(word)
            else:
                next_word = self.try_next_word(pos)
                if next_word == "," or next_word == ")":
                    name = word
                    if len(modifiers) > 0:
                        result.append({"type":type, "name":name, "modifiers":modifiers})
                    else:
                        result.append({"type":type, "name":name})
                else:
                    type = word
                    modifiers = []

        return result, pos

    def handle_returns(self, pos):
        result = []

        while True:
            word, pos = self.get_one_word(pos)
            if word == '(':
                self.stack.push(word)
                continue
            elif word == ',':
                continue
            elif word == ')':
                if self.stack.peek() != "(":
                    raise ParseErrorException("Parse Error!")
                else:
                    self.stack.pop()
                    break
            elif word in self.types:
                result.append(word)
            else:
                continue

        return result, pos

    def handle_function_body(self, pos):
        body, pos = self.read_until_stop(pos, "}", self.stack.depth())

        return body, pos

    def handle_function(self, pos):
        result = {}
        modifiers = []

        # function name
        word = self.try_next_word(pos)
        if word == "(":
            result["name"] = "fallback"
        else:
            word, pos = self.get_one_word(pos)
            result["name"] = word
        # function parameters
        word, pos = self.get_one_word(pos)
        if word == "(":
            self.stack.push(word)
            parameters, pos = self.handle_parameters(pos)
            if len(parameters) > 0:
                result["parameters"] = parameters

        while True:
            word, pos = self.get_one_word(pos)
            if word == "returns":
                returns, pos = self.handle_returns(pos)
                result["returns"] = returns
            elif word == ";":
                break
            elif word == "{":
                self.stack.push(word)
                function_body, pos = self.handle_function_body(pos)
                result["body"] = function_body
            elif word == "}":
                if self.stack.peek() != "{":
                    raise ParseErrorException("Parse Error!")
                else:
                    self.stack.pop()
                    break
            else:
                modifiers.append(word)

        if len(modifiers) > 0:
            result["modifiers"] = modifiers

        return result, pos

    def handle_variable(self, pos):
        result = {}
        modifiers = []

        while True:
            word, pos = self.get_one_word(pos)
            if word == ";":
                break
            if word == "[":
                self.stack.push("[")
                modifiers.append("array")
            if word == "]":
                if self.stack.peek() != "[":
                    raise ParseErrorException("Parse Error!")
                else:
                    self.stack.pop()
                    continue
            elif word in self.reserve_words:
                modifiers.append(word)
            elif word == "=":
                value, pos = self.get_one_sentence(pos)
                result["default_value"] = value
                break
            else:
                result["name"] = word

        if len(modifiers) > 0:
            result["modifiers"] = modifiers

        return result, pos

    def handle_event(self, pos):
        result = {}

        word, pos = self.get_one_word(pos)
        result["name"] = word

        while True:
            word, pos = self.get_one_word(pos)
            if word == ";":
                break
            elif word == "(":
                self.stack.push(word)
                parameters, pos = self.handle_parameters(pos)
                if len(parameters) > 0:
                    result["parameters"] = parameters

        return result, pos

    def handle_modifier_body(self, pos):
        return self.handle_function_body(pos)

    def handle_modifier(self, pos):
        result = {}

        word, pos = self.get_one_word(pos)
        result["name"] = word

        while True:
            word, pos = self.get_one_word(pos)
            if word == ";":
                break
            elif word == "(":
                self.stack.push("(")
                parameters, pos = self.handle_parameters(pos)
                if len(parameters) > 0:
                    result["parameters"] = parameters
            elif word == "{":
                self.stack.push("{")
                modifier_body, pos = self.handle_modifier_body(pos)
                result["body"] = modifier_body
            elif word == "}":
                if self.stack.peek() != "{":
                    raise ParseErrorException("Parse Error!")
                else:
                    self.stack.pop()
                    break

        return result, pos

    def handle_using(self, pos):
        result = {}

        word, pos = self.get_one_word(pos)
        result["from"] = word

        word, pos = self.get_one_word(pos)
        if word != "for":
            raise ParseErrorException("Parse using error!")

        word, pos = self.get_one_word(pos)
        result["target"] = word

        word, pos = self.get_one_word(pos)
        if word != ";":
            raise ParseErrorException("Parse using error!")

        return result, pos

    def handle_mapping(self, pos):
        result = {}

        while True:
            word, pos = self.get_one_word(pos)
            if word == ";":
                break
            elif word == "(":
                self.stack.push("(")
                continue
            elif word == ")":
                if self.stack.peek() != "(":
                    raise ParseErrorException("Parse Error, stack peek is {0}".format(self.stack.peek()))
                else:
                    self.stack.pop()
                    continue
            elif word == "mapping":
                continue
            elif word in self.types:
                continue
            else:
                result["name"] = word

        return result, pos

    def handle_struct(self, pos):
        result = {}
        fields = []

        word, pos = self.get_one_word(pos)
        result["name"] = word

        while True:
            word, pos = self.get_one_word(pos)
            if word == "{":
                self.stack.push("{")
                continue
            elif word == "}":
                if self.stack.peek() != "{":
                    raise ParseErrorException("Parse Error, stack peek is {0}".format(self.stack.peek()))
                else:
                    self.stack.pop()
                    break
            elif word == ";":
                continue
            elif word == "mapping":
                mapping, pos = self.handle_mapping(pos)
                mapping["type"] = word
                fields.append(mapping)
            elif word in self.types:
                type = word
                name, pos = self.get_one_word(pos)
                fields.append({"type":type, "name":name})

        if len(fields) > 0:
            result["fields"] = fields

        return result, pos

    def handle_enum(self, pos):
        result = {}
        definitions = []

        word, pos = self.get_one_word(pos)
        result["name"] = word

        while True:
            word, pos = self.get_one_word(pos)
            if word == "{":
                self.stack.push("{")
                continue
            elif word == "}":
                if self.stack.peek() != "{":
                    raise ParseErrorException("Parse Error, stack peek is {0}".format(self.stack.peek()))
                else:
                    self.stack.pop()
                    break
            elif word == ",":
                continue
            else:
                definitions.append(word)

        if len(definitions) > 0:
            result["definitions"] = definitions

        return result, pos

    def handle_constructor(self, pos):
        result = {}
        modifiers = []

        # parameters
        word, pos = self.get_one_word(pos)
        if word == "(":
            self.stack.push(word)
            parameters, pos = self.handle_parameters(pos)
            if len(parameters) > 0:
                result["parameters"] = parameters

        while True:
            word, pos = self.get_one_word(pos)
            if word == "{":
                self.stack.push(word)
                function_body, pos = self.handle_function_body(pos)
                result["body"] = function_body
            elif word == "}":
                if self.stack.peek() != "{":
                    raise ParseErrorException("Parse Error!")
                else:
                    self.stack.pop()
                    break
            else:
                modifiers.append(word)

        if len(modifiers) > 0:
            result["modifiers"] = modifiers

        return result, pos

    def handle_block_body(self, pos):
        result = {}
        functions = []
        variables = []
        events = []
        modifiers = []
        usings = []
        mappings = []
        structs = []
        enums = []

        while True:
            word, pos = self.get_one_word(pos)
            if word == "}":
                if self.stack.peek() != "{":
                    raise ParseErrorException("Parse Error!")
                else:
                    self.stack.pop()
                    break
            elif word in self.types:
                variable, pos = self.handle_variable(pos)
                variable["type"] = word
                variables.append(variable)
            elif word == "using":
                using, pos = self.handle_using(pos)
                using["type"] = word
                usings.append(using)
            elif word == "mapping":
                mapping, pos = self.handle_mapping(pos)
                mapping["type"] = word
                mappings.append(mapping)
            elif word == "event":
                event, pos = self.handle_event(pos)
                event["type"] = word
                events.append(event)
            elif word == "modifier":
                modifier, pos = self.handle_modifier(pos)
                modifier["type"] = word
                modifiers.append(modifier)
            elif word == "function":
                function, pos = self.handle_function(pos)
                function["type"] = word
                functions.append(function)
            elif word == "struct":
                struct, pos = self.handle_struct(pos)
                struct["type"] = word
                structs.append(struct)
            elif word == "constructor":
                constructor, pos = self.handle_constructor(pos)
                constructor["type"] = word
                result["constructor"] = constructor
            elif word == "enum":
                enum, pos = self.handle_enum(pos)
                enum["type"] = word
                enums.append(enum)
            else:
                variable, pos = self.handle_variable(pos)
                variable["type"] = word
                variables.append(variable)


        if len(functions) > 0:
            result["functions"] = functions
        if len(variables) > 0:
            result["variables"] = variables
        if len(usings) > 0:
            result["usings"] = usings
        if len(mappings) > 0:
            result["mappings"] = mappings
        if len(events) > 0:
            result["events"] = events
        if len(modifiers) > 0:
            result["modifiers"] = modifiers
        if len(structs) > 0:
            result["structs"] = structs
        if len(enums) > 0:
            result["enums"] = enums

        return result, pos

    def handle_pragma(self, pos):
        result = {}
        result["type"] = "pragma"

        content = []
        while True:
            word, pos = self.get_one_word(pos)
            if word != ';':
                content.append(word)
            else:
                break

        result["content"] = " ".join(content)

        return result, pos

    def handle_inheritance(self, pos):
        result = []

        while True:
            word, pos = self.get_one_word(pos)
            if word == '{':
                self.stack.push(word)
                break
            elif word == ",":
                continue
            else:
                result.append(word)

        return result, pos

    def handle_import(self, pos):
        result = {}
        result["type"] = "import"

        word, pos = self.get_one_word(pos)
        result["from"] = word

        word, pos = self.get_one_word(pos)
        if word == "as":
            word, pos = self.get_one_word(pos)
            result["as"] = word
            word, pos = self.get_one_word(pos)
            if word != ";":
                raise ParseErrorException("Parse Error!")

        return result, pos


    def handle_library(self, pos):
        result = {}
        result["type"] = "library"

        word, pos = self.get_one_word(pos)
        result["name"] = word

        word, pos = self.get_one_word(pos)
        if word == "{":
            self.stack.push(word)
            body, pos = self.handle_block_body(pos)
        elif word == "is":
            inheritance, pos = self.handle_inheritance(pos)
            result["inheritance"] = inheritance
            body, pos = self.handle_block_body(pos)

        result["body"] = body

        return result, pos

    def handle_interface(self, pos):
        result = {}
        result["type"] = "interface"

        word, pos = self.get_one_word(pos)
        result["name"] = word

        word, pos = self.get_one_word(pos)
        if word == "{":
            self.stack.push(word)
            body, pos = self.handle_block_body(pos)
        elif word == "is":
            inheritance, pos = self.handle_inheritance(pos)
            result["inheritance"] = inheritance
            body, pos = self.handle_block_body(pos)

        result["body"] = body

        return result, pos

    def handle_contract(self, pos):
        result = {}
        result["type"] = "contract"

        word, pos = self.get_one_word(pos)
        result["name"] = word

        word, pos = self.get_one_word(pos)
        if word == "{":
            self.stack.push(word)
            body, pos = self.handle_block_body(pos)
        elif word == "is":
            inheritance, pos = self.handle_inheritance(pos)
            result["inheritance"] = inheritance
            body, pos = self.handle_block_body(pos)

        result["body"] = body

        return result, pos

    def get_one_word(self, pos):
        start = pos
        while self.content[pos] == ' ':
            pos += 1
            start = pos

        if self.content[pos] == self.EF:
            return self.content[pos], pos
        if self.content[pos] == ";":
            return self.content[pos], pos + 1
        if self.content[pos] == ",":
            return self.content[pos], pos + 1
        if self.is_limiter(self.content[pos]):
            return self.content[pos], pos + 1
        else:
            while not self.is_terminator(self.content[pos]):
                # print(self.content[pos])
                pos += 1
            return self.content[start:pos], pos

    def try_next_word(self, pos):
        start = pos
        while self.content[pos] == ' ':
            pos += 1
            start = pos

        if self.content[pos] == "$":
            return self.content[pos]
        if self.content[pos] == ";":
            return self.content[pos]
        if self.content[pos] == ",":
            return self.content[pos]
        if self.is_limiter(self.content[pos]):
            return self.content[pos]
        else:
            while not self.is_terminator(self.content[pos]):
                # print(self.content[pos])
                pos += 1
            return self.content[start:pos]

    def read_until_stop(self, pos, stop, stack_depth):
        depth = stack_depth
        start = pos
        while self.content[pos] == ' ':
            pos += 1
            start = pos

        while self.content[pos] != stop or self.stack.depth() != depth:
            if self.content[pos] == "(":
                self.stack.push("(")
            elif self.content[pos] == ")":
                if self.stack.peek() != "(":
                    raise ParseErrorException("Parse Error!")
                else:
                    self.stack.pop()
            elif self.content[pos] == "[":
                self.stack.push("[")
            elif self.content[pos] == "]":
                if self.stack.peek() != "[":
                    raise ParseErrorException("Parse Error!")
                else:
                    self.stack.pop()
            elif self.content[pos] == "{":
                self.stack.push("{")
            elif self.content[pos] == "}":
                if self.stack.peek() != "{":
                    raise ParseErrorException("Parse Error!")
                else:
                    self.stack.pop()

            pos += 1

        return self.content[start:pos], pos

    def get_one_sentence(self, pos):
        start = pos
        while self.content[pos] == ' ':
            pos += 1
            start = pos

        if self.content[pos] == "}":
            return None, pos + 1
        else:
            while self.content[pos] != ";":
                # print(self.content[pos])
                pos += 1
            return self.content[start:pos + 1], pos + 1

    def parse(self):
        result_list = []
        pos = 0

        while self.content[pos] != self.EF:
            # get one word
            word, pos = self.get_one_word(pos)

            # parse over
            if word == self.EF:
                break

            handler = None
            for block in self.blocks:
                if word == block.key_word:
                    handler = block.handler
                    break

            if handler != None:
                result, pos = block.handler(pos)
                result_list.append(result)
            else:
                # print("Can't handle current block!")
                raise ParseErrorException("Can't handle current block, word = {0}".format(word))

        return result_list


class Trim(object):
    COMMENT_RX = re.compile("(?<!:)\\/\\/.*|\\/\\*(\\s|.)*?\\*\\/", re.MULTILINE)
    SPACE_RX = re.compile('[\n\r$\s]+', re.MULTILINE)

    @classmethod
    def strip_spaces(cls, content):
        return cls.SPACE_RX.sub(' ', content)

    @classmethod
    def strip_comments(cls, content):
        return cls.COMMENT_RX.sub('', content)
