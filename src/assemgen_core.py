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

class RISCV(GenericTarget):
    gprs_list = [f"x{i}" for i in range(1, 32)]
    csrs_list = ["mstatus", "mepc"]
    fprs_list = [f"f{i}" for i in range(32)]

    def __init__(self, json):
        super().__init__(json)
        assert self.arch_name == "riscv"
        self.xlen = self.arch["xlen"]

        self.isa_state_table = self.gprs_list + self.csrs_list + self.fprs_list

    def parse_template(self, template: str) -> str:
        for v_str in self.isa_state_table:
            #如果self.isa_state[v_str]找不到对应的值，就用默认值0
            template.replace(f"${v_str}",Value(self.get_isa_state().get_or_else(v_str,"0")).to_hex())
            

def assemgen_core(target: GenericTarget,template:str)->str:
    pass

# test
import unittest
class TestAssemgen(unittest.TestCase):
    pass