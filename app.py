import os, anthropic, ephem, calendar
from flask import Flask, render_template, request, jsonify
from datetime import datetime, date

app = Flask(__name__)
client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

def get_luna_dia(fecha):
    moon = ephem.Moon(fecha)
    p = moon.phase
    if p < 7:    return {'fase':'nueva',    'emoji':chr(0x1F311),'pct':round(p,1)}
    elif p < 30: return {'fase':'creciente', 'emoji':chr(0x1F312),'pct':round(p,1)}
    elif p < 55: return {'fase':'cuarto_c',  'emoji':chr(0x1F313),'pct':round(p,1)}
    elif p < 80: return {'fase':'gibosa_c',  'emoji':chr(0x1F314),'pct':round(p,1)}
    elif p < 93: return {'fase':'llena',     'emoji':chr(0x1F315),'pct':round(p,1)}
    elif p < 107:return {'fase':'gibosa_m',  'emoji':chr(0x1F316),'pct':round(p,1)}
    elif p < 130:return {'fase':'cuarto_m',  'emoji':chr(0x1F317),'pct':round(p,1)}
    else:        return {'fase':'menguante', 'emoji':chr(0x1F318),'pct':round(p,1)}

ACTIVIDADES = {
    'nueva':    ['sembrar','transplantar','regar'],
    'creciente':['esquejes','regar','abonar'],
    'cuarto_c': ['abonar','podar','esquejes'],
    'gibosa_c': ['abonar','regar','contra_plagas'],
    'llena':    ['cosechar','esquejes','regar'],
    'gibosa_m': ['podar','contra_plagas','regar'],
    'cuarto_m': ['contra_plagas','podar','abonar'],
    'menguante':['podar','descanso','preparar'],
}

NOMBRES_FASE = {
    'nueva':'Luna Nueva','creciente':'Luna Creciente',
    'cuarto_c':'Cuarto Creciente','gibosa_c':'Gibosa Creciente',
    'llena':'Luna Llena','gibosa_m':'Gibosa Menguante',
    'cuarto_m':'Cuarto Menguante','menguante':'Luna Menguante'
}

RECS_FASE = {
    'nueva':'Siembra y trasplanta. Energia concentrada en raices.',
    'creciente':'Ideal para esquejes y crecimiento vegetativo.',
    'cuarto_c':'Aplica fertilizantes y poda. Crecimiento activo.',
    'gibosa_c':'Maxima absorcion de nutrientes. Riego abundante.',
    'llena':'Cosecha ahora para mayor potencia de resina.',
    'gibosa_m':'Reduce riego. Ideal poda y limpieza de planta.',
    'cuarto_m':'Aplica pesticidas biologicos y compost.',
    'menguante':'Periodo de descanso. Prepara sustratos.'
}

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/moon')
def api_moon():
    now = datetime.utcnow()
    luna = get_luna_dia(now)
    fase = luna['fase']
    nn = ephem.next_new_moon(now)
    nf = ephem.next_full_moon(now)
    return jsonify({'phase_pct':luna['pct'],'name':NOMBRES_FASE[fase],
        'emoji':luna['emoji'],'rec':RECS_FASE[fase],'fase':fase,
        'actividades':ACTIVIDADES[fase],
        'next_new':nn.datetime().strftime('%d/%m/%Y'),
        'next_full':nf.datetime().strftime('%d/%m/%Y')})

@app.route('/api/moon/mes')
def api_moon_mes():
    anio = int(request.args.get('anio', datetime.utcnow().year))
    mes  = int(request.args.get('mes',  datetime.utcnow().month))
    total = calendar.monthrange(anio, mes)[1]
    dias = []
    for d in range(1, total+1):
        fecha = date(anio, mes, d)
        luna = get_luna_dia(fecha)
        fase = luna['fase']
        dias.append({'dia':d,'emoji':luna['emoji'],'fase':fase,
                     'pct':luna['pct'],'actividades':ACTIVIDADES[fase],
                     'nombre':NOMBRES_FASE[fase],'rec':RECS_FASE[fase]})
    return jsonify({'dias':dias,'anio':anio,'mes':mes})

@app.route('/api/chat', methods=['POST'])
def api_chat():
    msgs = request.json.get('messages',[])
    if not msgs: return jsonify({'error':'Sin mensajes'}), 400
    r = client.messages.create(
        model='claude-sonnet-4-20250514', max_tokens=1024,
        system=('Eres CannaBot, experto cultivador y procesador de cannabis con 20 anos de experiencia. '
                'Conoces perfectamente sustratos, plagas, esquejes, hidroponia, cultivo indoor y outdoor, '
                'calendarios lunares, cosecha, curado, secado, extraccion de concentrados, '
                'medicina con cannabis, recetas de cocina con cannabis y mucho mas. '
                'Respondes en espanol argentino, eres directo y practico.'),
        messages=msgs)
    return jsonify({'reply': r.content[0].text})

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    d = request.json
    imagen = d.get('image')
    media_type = d.get('media_type','image/jpeg')
    if not imagen: return jsonify({'error':'Sin imagen'}), 400
    r = client.messages.create(
        model='claude-sonnet-4-20250514', max_tokens=1500,
        system=('Eres experto fitopatologista y nutricionista en cannabis. '
                'Analiza la foto y responde en espanol argentino con este formato:\n'
                'ESTADO GENERAL:\n[descripcion]\n\n'
                'PROBLEMAS DETECTADOS:\n[lista]\n\n'
                'DIAGNOSTICO:\n[diagnostico]\n\n'
                'PLAGAS O ENFERMEDADES:\n[detalle]\n\n'
                'CARENCIAS NUTRICIONALES:\n[deficiencias]\n\n'
                'EXCESOS:\n[si hay]\n\n'
                'TRATAMIENTO PASO A PASO:\n[pasos]\n\n'
                'MEZCLA DE ABONO RECOMENDADA:\n[mezcla especifica]'),
        messages=[{'role':'user','content':[
            {'type':'image','source':{'type':'base64','media_type':media_type,'data':imagen}},
            {'type':'text','text':'Analiza esta planta de cannabis en detalle. Diagnostico completo de plagas, carencias, excesos y tratamiento incluyendo mezcla de abono.'}
        ]}])
    return jsonify({'analysis': r.content[0].text})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)), debug=False)
