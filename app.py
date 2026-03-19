import os, anthropic, ephem
from flask import Flask, render_template, request, jsonify
from datetime import datetime
import math

app = Flask(__name__)
client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

def get_luna_dia(fecha):
    moon = ephem.Moon(fecha)
    p = moon.phase
    if p < 7:    return {'fase':'nueva','emoji':chr(0x1F311),'pct':round(p,1)}
    elif p < 30: return {'fase':'creciente','emoji':chr(0x1F312),'pct':round(p,1)}
    elif p < 55: return {'fase':'cuarto_c','emoji':chr(0x1F313),'pct':round(p,1)}
    elif p < 80: return {'fase':'gibosa_c','emoji':chr(0x1F314),'pct':round(p,1)}
    elif p < 93: return {'fase':'llena','emoji':chr(0x1F315),'pct':round(p,1)}
    elif p < 107:return {'fase':'gibosa_m','emoji':chr(0x1F316),'pct':round(p,1)}
    elif p < 130:return {'fase':'cuarto_m','emoji':chr(0x1F317),'pct':round(p,1)}
    else:        return {'fase':'menguante','emoji':chr(0x1F318),'pct':round(p,1)}

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

def get_luna():
    now = datetime.utcnow()
    luna = get_luna_dia(now)
    nn = ephem.next_new_moon(now)
    nf = ephem.next_full_moon(now)
    nombres = {'nueva':'Luna Nueva','creciente':'Luna Creciente',
               'cuarto_c':'Cuarto Creciente','gibosa_c':'Gibosa Creciente',
               'llena':'Luna Llena','gibosa_m':'Gibosa Menguante',
               'cuarto_m':'Cuarto Menguante','menguante':'Luna Menguante'}
    recs = {'nueva':'Siembra y trasplanta. Energia concentrada en raices.',
            'creciente':'Ideal para esquejes y crecimiento vegetativo.',
            'cuarto_c':'Aplica fertilizantes y poda. Crecimiento activo.',
            'gibosa_c':'Maxima absorcion de nutrientes. Riego abundante.',
            'llena':'Cosecha ahora para mayor potencia de resina.',
            'gibosa_m':'Reduce riego. Ideal poda y limpieza de planta.',
            'cuarto_m':'Aplica pesticidas biologicos y compost.',
            'menguante':'Periodo de descanso. Prepara sustratos.'}
    fase = luna['fase']
    return {'phase_pct':luna['pct'],'name':nombres[fase],'emoji':luna['emoji'],
            'rec':recs[fase],'fase':fase,
            'actividades':ACTIVIDADES[fase],
            'next_new':nn.datetime().strftime('%d/%m/%Y'),
            'next_full':nf.datetime().strftime('%d/%m/%Y')}

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/moon')
def api_moon(): return jsonify(get_luna())

@app.route('/api/moon/mes')
def api_moon_mes():
    from datetime import date, timedelta
    anio = int(request.args.get('anio', datetime.utcnow().year))
    mes  = int(request.args.get('mes',  datetime.utcnow().month))
    import calendar
    total = calendar.monthrange(anio, mes)[1]
    dias = []
    for d in range(1, total+1):
        fecha = date(anio, mes, d)
        luna = get_luna_dia(fecha)
        fase = luna['fase']
        dias.append({'dia':d,'emoji':luna['emoji'],'fase':fase,
                     'pct':luna['pct'],'actividades':ACTIVIDADES[fase]})
    return jsonify({'dias':dias,'anio':anio,'mes':mes})

@app.route('/api/chat', methods=['POST'])
def api_chat():
    msgs = request.json.get('messages',[])
    if not msgs: return jsonify({'error':'Sin mensajes'}), 400
    r = client.messages.create(
        model='claude-sonnet-4-20250514', max_tokens=1024,
        system='Eres CannaBot, experto cultivador de cannabis con 20 anos de experiencia. Conoces perfectamente sustratos, plagas, esquejes, hidroponia, cultivo indoor y outdoor, calendarios lunares, horas de luz, nutricion, variedades y tecnicas de poda. Respondes en espanol argentino, eres directo y practico.',
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
        system=(
            'Eres un experto fitopatologista y nutricionista especializado en cannabis. '
            'Analiza la foto de la planta y responde en espanol argentino con este formato exacto:\n'
            'ESTADO GENERAL:\n[descripcion]\n\n'
            'PROBLEMAS DETECTADOS:\n[lista de problemas]\n\n'
            'DIAGNOSTICO:\n[diagnostico probable]\n\n'
            'PLAGAS O ENFERMEDADES:\n[si hay, cuales y como se ven]\n\n'
            'CARENCIAS NUTRICIONALES:\n[deficiencias detectadas]\n\n'
            'EXCESOS:\n[si hay excesos de nutrientes]\n\n'
            'TRATAMIENTO PASO A PASO:\n[pasos concretos]\n\n'
            'MEZCLA DE ABONO RECOMENDADA:\n[si necesita abonar, que mezcla especifica usar]'
        ),
        messages=[{'role':'user','content':[
            {'type':'image','source':{'type':'base64','media_type':media_type,'data':imagen}},
            {'type':'text','text':'Analiza esta planta de cannabis en detalle. Dame diagnostico completo de plagas, carencias, excesos y como tratarlos incluyendo mezcla de abono si hace falta.'}
        ]}])
    return jsonify({'analysis': r.content[0].text})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)), debug=False)
