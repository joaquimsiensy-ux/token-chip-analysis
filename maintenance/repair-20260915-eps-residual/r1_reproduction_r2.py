import ast, subprocess
from collections import deque
from pathlib import Path
p = "scripts/report/entity_source_trace.py"
names = {"VectorAccount", "LayeredAccount", "make_account",
         "simulate", "gap_eps", "policy_detail"}
def load(s):
    ns = dict(deque=deque, EPS=1e-6, GAP_EPS_REL=1e-13,
              ENTITY_NODE="@ENTITY",
              ORDER_AMBIGUOUS_KEY=("UNRESOLVED","order_ambiguous",None))
    nodes = [n for n in ast.parse(s).body
             if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),p,"exec"),ns)
    return ns
models = [
    load(subprocess.check_output(
        ["git","--no-optional-locks","show","HEAD:"+p],text=True)),
    load(Path(p).read_text())]
z = "0x0000000000000000000000000000000000000000"
cases = [
    ("mixed",
     [("X","A",2**60),("X","A",1),("A","D",2**60)],
     10*2**90, {"X","A"}, {}),
    ("small_flip",
     [(z,"M",100),("X","M",100),("M","D",100)],
     10**6, {"X","M"}, {z:("PROVEN_ORIGIN","mint",z)})]
for name,rows,supply,ancestors,terms in cases:
    detail = []
    for i,m in enumerate(models):
        edges = [(86400,0,j,0,True,j,f,t,a)
                 for j,(f,t,a) in enumerate(rows)]
        kw = {"gap_eps":m["gap_eps"](supply)} if i else {}
        pd = {
            pol:m["policy_detail"](m["simulate"](
                edges,{"D"},ancestors,terms,{},pol,172799,**kw)["current"])
            for pol in ("pro_rata","fifo","lifo")}
        detail.append(pd)
        print(name,("HEAD","WORKTREE")[i],
              {pol:sum(int(r["raw"]) for r in rs) for pol,rs in pd.items()})
    print("policy_details_equal =",detail[0]==detail[1])
    if name=="small_flip":
        print("tops =",{pol:rs[0]["terminal"] for pol,rs in detail[1].items()})
