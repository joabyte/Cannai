import os, anthropic, ephem
from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)
client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

def get_luna():
    now = datetime.utcnow()
    moon = ephem.Moon(now)
    p = moon.phase
    proxima_nueva = ephem.next_new_moon(now)
    proxima_llena = ephem.next_full_moon(now)
    if p < 7:
        nombre, emoji, rec = 'Luna Nueva', chr(0x1F311), 'Siembra semillas y trasplanta. Energia concentrada en raices.'
    elif p < 30:
        nombre, emoji, rec = 'Luna Creciente', chr(0x1F312), 'Ideal para esquejes y crecimiento vegetativo.'
    elif p < 55:
        nombre, emoji, rec = 'Cuarto Creciente', chr(0x1F313), 'Aplica fertilizantes y poda. Crecimiento activo.'
    elif p < 80:
        nombre, emoji, rec = 'Gibosa Creciente', chr(0x1F314), 'Maxima absorcion de nutrientes. Riego abundante.'
    elif p < 93:
        nombre, emoji, rec = 'Luna Llena', chr(0x1F315), 'Cosecha ahora para mayor potencia de resina.'
    elif p < 107:
        nombre, emoji, rec = 'Gibosa Menguante', chr(0x1F316), 'Reduce riego. Ideal para poda y limpieza de planta.'
    elif p < 130:
        nombre, emoji, rec = 'Cuarto Menguante', chr(0x1F317), 'Aplica pesticidas biologicos y compost.'
    else:
        nombre, emoji, rec = 'Luna Menguante', chr(0x1F318), 'Periodo de descanso. Prepara sustratos y herramientas.'
    return {
        'phase_pct': round(p, 1),
        'name': nombre,
        'emoji': emoji,
        'rec': rec,
        'next_new': proxima_nueva.datetime().strftime('%d/%m/%Y'),
        'next_full': proxima_llena.datetime().strftime('%d/%m/%Y')
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/moon')
def api_moon():
    return jsonify(get_luna())

@app.route('/api/chat', methods=['POST'])
def api_chat():
    datos = request.json
    mensajes = datos.get('messages', [])
    if not mensajes:
        return jsonify({'error': 'Sin mensajes'}), 400
    respuesta = client.messages.create(
        model='claude-sonnet-4-20250514',
        max_tokens=1024,
        system=(
            'Eres CannaBot, un experto cultivador de cannabis con 20 anos de experiencia. '
            'Conoces perfectamente sustratos, plagas, esquejes, hidroponia, cultivo indoor y outdoor, '
            'calendarios lunares, horas de luz, nutricion, variedades, tecnicas de poda y mucho mas. '
            'Respondes siempre en espanol argentino, eres directo y practico.'
        ),
        messages=mensajes
    )
    return jsonify({'reply': respuesta.content[0].text})

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    datos = request.json
    imagen = datos.get('image')
    media_type = datos.get('media_type', 'image/jpeg')
    if not imagen:
        return jsonify({'error': 'Sin imagen'}), 400
    respuesta = client.messages.create(
        model='claude-sonnet-4-20250514',
        max_tokens=1200,
        system=(
            'Eres un experto fitopatologista especializado en cannabis. '
            'Analiza la foto de la planta y responde en espanol argentino con: '
            '1) Estado general de la planta '
            '2) Problemas detectados (deficiencias, plagas, hongos, quemaduras, etc) '
            '3) Diagnostico probable '
            '4) Tratamiento recomendado paso a paso'
        ),
        messages=[{
            'role': 'user',
            'content': [
                {'type': 'image', 'source': {'type': 'base64', 'media_type': media_type, 'data': imagen}},
                {'type': 'text', 'text': 'Que le pasa a esta planta de cannabis y como la trato?'}
            ]
        }]
    )
    return jsonify({'analysis': respuesta.content[0].text})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
