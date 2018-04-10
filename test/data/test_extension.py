import pdsc

@pdsc.register_determiner('test')
def test_determiner(label_file):
    return pdsc.generic_determiner(label_file, 'TEST INSTRUMENT')

@pdsc.register_table('test')
class TestTable(pdsc.CtxTable): pass

@pdsc.register_localizer('test')
class TestLocalizer(pdsc.CtxLocalizer): pass
