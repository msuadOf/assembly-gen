# env python3
import JSON

json_file_path=args....

with open... :
	json_con= #json内容并用JSON转成python数据
class Value:
	"""
 use: Value("64'b0010_0001")代表64位的无符号数字
	"""
	def __init__(self,exp:str):
			self.unsigned(self,exp)

class GenericTarget():

    
	def __init__(self,json,template_path="resource/riscv/template.S"):
		self.json=json
		self.arch=self.json["arch"]
  		self.arch_name=self.arch["name"]
		self.isa_state=self.json["isa-state"]
		self.test_ins=...
		self.template_path=template_path

    def get_arch(self):
        self.arch
    def get_isa_state(self):
        self.isa_state

	def parse_template(self,template:str)

class RISCV(GenericTarget):


    def __init__(self,json):
        super.__init__(json)
        assert(self.arch_name=="riscv")
        self.xlen=self.arch["xlen"]
        
		gprs=["x0","x1"...]
		csrs=["mstatus",...]
		self.isa_state_table=gprs.append(csrs)
    def parse_template(self,template:str)->str:
        for v_str in self.isa_state_table:
            #如果self.isa_state[v_str]找不到对应的值，就用默认值0
            template.replace(f"${v_str}",Value(self.get_isa_state().get_or_else(v_str,"0")).to_hex())
            
    def gen_assembly(self)->str:
        with open(self.template_path) as f:
            self.parse_template(f.read())
            
