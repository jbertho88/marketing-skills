"""Validate the subset of JSON Schema used by the packaged findings contract."""
def validate(value, schema, path='$'):
    types={'object':dict,'array':list,'string':str,'number':(int,float),'boolean':bool,'null':type(None)}
    kind=schema.get('type')
    allowed=kind if isinstance(kind,list) else [kind] if kind else []
    if allowed and not any(isinstance(value,types[t]) and not (t=='number' and isinstance(value,bool)) for t in allowed):
        raise ValueError(f'{path}: expected {kind}')
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError(f'{path}: invalid enum value')
    if isinstance(value,dict):
        for key in schema.get('required',[]):
            if key not in value:
                raise ValueError(f'{path}: missing {key}')
        for key,item in value.items():
            rule=schema.get('properties',{}).get(key,schema.get('additionalProperties',{}))
            if rule is False:
                raise ValueError(f'{path}: unexpected {key}')
            if isinstance(rule,dict):
                validate(item,rule,path+'.'+key)
    if isinstance(value,list):
        if schema.get('uniqueItems') and len({repr(x) for x in value})!=len(value):
            raise ValueError(f'{path}: duplicate items')
        for i,item in enumerate(value):
            validate(item,schema.get('items',{}),f'{path}[{i}]')
    if isinstance(value,str) and len(value)<schema.get('minLength',0):
        raise ValueError(f'{path}: empty string')
    if isinstance(value,(int,float)) and not isinstance(value,bool):
        import math
        if not math.isfinite(value) or value<schema.get('minimum',float('-inf')) or value>schema.get('maximum',float('inf')):
            raise ValueError(f'{path}: out of bounds')
