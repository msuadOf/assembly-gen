class GenericTarget:
    def __init__(self, json, template_path="resource/riscv/template.S"):
        self.json = json
        self.arch = self.json["arch"]
        self.arch_name = self.arch["name"]
        self.isa_state = self.json["isa-state"]
        self.test_ins = ...
        self.template_path = template_path

    def get_arch(self):
        self.arch

    def get_isa_state(self):
        self.isa_state

    def parse_template(self, template: str):
        pass


def assemgen_core(target: GenericTarget,template:str)->str:
    pass

# test
import unittest
class TestAssemgen(unittest.TestCase):
    pass