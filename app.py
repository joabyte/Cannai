import os, anthropic, ephem, calendar
from flask import Flask, render_template, request, jsonify
from datetime import datetime, date

app = Flask(__name__)
client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

def get_luna_dia(fecha):
    moon = ephem.Moon(fecha)
    sun  = ephem.Sun(fecha)
    moon.compute(fecha)
    sun.compute(fecha)
    p = moon.phase
    # Elongacion: angulo entre luna y sol en el cielo
    # Usamos la diferencia de ascension recta para saber si crece o mengua
    elong = float(moon.elong) * 180.0 / 3.141592653589793
    creciendo = elong >= 0  # positivo = luna al este del sol = creciente
    if p < 2:    return {'fase':'nueva',    'emoji':chr(0x1F311),'pct':round(p,1)}
    elif p < 45 and creciendo:  return {'fase':'creciente', 'emoji':chr(0x1F312),'pct':round(p,1)}
    elif p < 55 and creciendo:  return {'fase':'cuarto_c',  'emoji':chr(0x1F313),'pct':round(p,1)}
    elif p < 98 and creciendo:  return {'fase':'gibosa_c',  'emoji':chr(0x1F314),'pct':round(p,1)}
    elif p >= 98: return {'fase':'llena',     'emoji':chr(0x1F315),'pct':round(p,1)}
    elif p >= 55 and not creciendo: return {'fase':'gibosa_m',  'emoji':chr(0x1F316),'pct':round(p,1)}
    elif p >= 45 and not creciendo: return {'fase':'cuarto_m',  'emoji':chr(0x1F317),'pct':round(p,1)}
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

@app.route('/manifest.json')
def manifest():
    from flask import Response
    import json
    data = {
        'name': 'CannaGuia Pro',
        'short_name': 'Cannai',
        'description': 'Tu asistente de cultivo de cannabis con IA',
        'start_url': '/',
        'scope': '/',
        'display': 'standalone',
        'background_color': '#060e06',
        'theme_color': '#4ade80',
        'orientation': 'portrait-primary',
        'lang': 'es',
        'categories': ['lifestyle', 'health'],
        'icons': [
            {'src': '/icon-192.png', 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any maskable'},
            {'src': '/icon-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any maskable'}
        ]
    }
    resp = Response(json.dumps(data), mimetype='application/manifest+json')
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp

@app.route('/sw.js')
def service_worker():
    from flask import Response
    sw = 'const CACHE="cannai-v1";self.addEventListener("install",e=>{self.skipWaiting();});self.addEventListener("activate",e=>{e.waitUntil(clients.claim());});self.addEventListener("fetch",e=>{e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));});'
    resp = Response(sw, mimetype='application/javascript')
    resp.headers['Service-Worker-Allowed'] = '/'
    return resp

@app.route('/icon-192.png')
def icon192():
    from flask import Response
    import base64
    # PNG verde 192x192 minimo
    png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAYAAABS3GwHAAAAuUlEQVR4nO3BMQEAAADCoPVP7WsIoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAeAMBuAABHgAAAABJRU5ErkJggg==')
    return Response(png, mimetype='image/png')

@app.route('/icon-512.png')
def icon512():
    from flask import Response
    import base64
    png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAYAAAD0eNT6AAAAvUlEQVR4nO3BMQEAAADCoPVP7WsIoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAeAMBOAABKgAAAABJRU5ErkJggg==')
    return Response(png, mimetype='image/png')
