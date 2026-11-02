import sys, tempfile, importlib.metadata, math
from qdrant_client import QdrantClient, models
from store import Catalog

def rows():
    return [{"id":i,"vector":[1.0,float(i)/10,0.1],"payload":{"tenant":"alpha" if i%2==0 else "beta","label":f"item-{i}","retained":"keep"}} for i in range(37)]

def smoke():
    assert importlib.metadata.version("qdrant-client")=="1.15.1"
    c=QdrantClient(":memory:");c.close()
    print("SMOKE PASS: pinned SDK and isolated local client")

def search():
    c=Catalog();c.add(rows())
    assert c.search([1.0,0.0,0.1],"alpha",3)==[0,2,4], "Expected nearest alpha IDs, including when a beta point ranks between them"
    assert c.search([1.0,0.0,0.1],"beta",2)==[1,3]
    assert c.search([1.0,0.0,0.1],"missing",3)==[]
    c.close();print("SEARCH PASS: filtered ranking and empty tenant")

def export():
    c=Catalog();c.add(rows())
    assert sorted(c.export("alpha",2))==list(range(0,37,2)), "Expected every alpha point across pages exactly once"
    assert sorted(c.export("beta",3))==list(range(1,37,2))
    assert c.export("missing",2)==[]
    c.close();print("EXPORT PASS: complete filtered exports across multiple pages")

def persistence():
    with tempfile.TemporaryDirectory() as d:
        seed=QdrantClient(path=d)
        seed.create_collection("catalog",vectors_config=models.VectorParams(size=3,distance=models.Distance.COSINE))
        seed.upsert("catalog",points=[models.PointStruct(**r) for r in rows()],wait=True);seed.close()
        c=Catalog(d);c.patch(4,{"label":"revised"});c.close()
        check=QdrantClient(path=d)
        assert check.count("catalog",exact=True).count==37, "Existing records must survive reopening"
        got={p.id:p for p in check.retrieve("catalog",ids=[4,5],with_vectors=True)}
        assert got[4].payload=={"tenant":"alpha","label":"revised","retained":"keep"}
        assert got[5].payload=={"tenant":"beta","label":"item-5","retained":"keep"}
        assert len(got[4].vector)==3
        check.close()
    print("PERSISTENCE PASS: read-back after reopen preserves data and updates only requested fields")

if __name__=="__main__":
    {"smoke":smoke,"search":search,"export":export,"persistence":persistence}[sys.argv[1]]()
