"""Conservative candidate comparison; never asserts installation compatibility."""
import re

LABELS = {'TIP_USTROYSTVA':'тип устройства','KOLICHESTVO_POLYUSOV':'полюса','NOMINALNYY_TOK':'номинальный ток',
'NOMINALNOE_NAPRYAZHENIE':'напряжение','KHARAKTERISTIKA_SRABATYVANIYA':'характеристика срабатывания',
'NOMINALNYY_OTKLYUCHAYUSHCHIY_DIFFERENTSIALNYY_TOK':'ток утечки','TIP_SVETILNIKA':'тип светильника',
'TIP_TSOKOLYA':'цоколь','SPOSOB_MONTAZHA':'монтаж','TIP_ISTOCHNIKA':'источник света'}


def norm(value):
    return re.sub(r'\s+','',str(value).lower()).replace('a','а').replace('v','в')


def comparison(original, candidate):
    if original.get('warnings') or candidate.get('warnings') or str(original['id']) == str(candidate['id']): return None
    try:
        if float(candidate.get('quantity',0)) <= 0: return None
    except (TypeError,ValueError): return None
    a,b=original.get('properties') or {},candidate.get('properties') or {}
    if a.get('TIP_USTROYSTVA'):
        required=['TIP_USTROYSTVA','KOLICHESTVO_POLYUSOV','NOMINALNYY_TOK','NOMINALNOE_NAPRYAZHENIE']
        # Protective device properties may not be silently dropped.
        required += [k for k in ['KHARAKTERISTIKA_SRABATYVANIYA','NOMINALNYY_OTKLYUCHAYUSHCHIY_DIFFERENTSIALNYY_TOK'] if a.get(k) or b.get(k)]
    elif a.get('TIP_SVETILNIKA'):
        required=['TIP_SVETILNIKA','TIP_TSOKOLYA','SPOSOB_MONTAZHA','TIP_ISTOCHNIKA']
    else: return None
    if any(not a.get(k) or not b.get(k) or norm(a[k]) != norm(b[k]) for k in required): return None
    shared=[LABELS[k]+': '+str(a[k]).strip() for k in required]
    differences=[k+': '+str(a[k])+' → '+str(b[k]) for k in a.keys() & b.keys()
                 if k in ('TORGOVAYA_MARKA','SVETOVOY_POTOK_LM','TIP_RASSEIVATELYA_','MATERIAL_KORPUSA') and norm(a[k])!=norm(b[k])]
    return {'for_article':original.get('article'),'matches':shared,'differences':differences,
            'caution':'Кандидат на замену по перечисленным полям. Габариты, условия эксплуатации и полную совместимость должен подтвердить специалист.'}
