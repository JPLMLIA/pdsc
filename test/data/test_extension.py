import pdsc

@pdsc.register_determiner('test')
def my_determiner(label_file):
    return pdsc.generic_determiner(label_file, 'TEST INSTRUMENT')

@pdsc.register_table('test')
class MyTable(pdsc.CtxTable): pass

@pdsc.register_localizer('test')
class MyLocalizer(pdsc.CtxLocalizer): pass
