import json
import requests

# Configuración de Odoo
ODOO_URL = 'http://localhost:8069/jsonrpc'
DATABASE = 'odooDB'
USERNAME = 'odoo'
PASSWORD = 'myodoo'

def odoo_login():
    """Realiza login en Odoo y devuelve el uid."""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "common",
            "method": "login",
            "args": [DATABASE, USERNAME, PASSWORD],
        },
        "id": 1,
    }
    response = requests.post(ODOO_URL, headers=headers, data=json.dumps(payload))
    uid = response.json().get('result')
    if uid:
        print(f"Conectado a Odoo con UID {uid}")
        return uid
    else:
        print("Error al conectarse a Odoo")
        exit(1)

def get_partner_by_email(email, uid):
    """Busca un contacto (res.partner) por correo electrónico."""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                DATABASE,
                uid,
                PASSWORD,
                'res.partner',
                'search_read',
                [[['email', '=', email]]],
                {'fields': ['id', 'name', 'email', 'phone', 'city']}
            ]
        },
        "id": 2,
    }
    response = requests.post(ODOO_URL, headers=headers, data=json.dumps(payload))
    result = response.json().get('result')
    if result and len(result) > 0:
        return result[0]
    return None

def create_partner(data, uid):
    """Crea un nuevo contacto en res.partner."""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                DATABASE,
                uid,
                PASSWORD,
                'res.partner',
                'create',
                [data]
            ]
        },
        "id": 3,
    }
    response = requests.post(ODOO_URL, headers=headers, data=json.dumps(payload))
    partner_id = response.json().get('result')
    if partner_id:
        print(f"Contacto creado con ID: {partner_id}")
    else:
        print("Error al crear el contacto")
    return partner_id

def update_partner(partner_id, data, uid):
    """Actualiza un contacto existente."""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                DATABASE,
                uid,
                PASSWORD,
                'res.partner',
                'write',
                [[partner_id], data]
            ]
        },
        "id": 4,
    }
    response = requests.post(ODOO_URL, headers=headers, data=json.dumps(payload))
    result = response.json().get('result')
    if result:
        print(f"Contacto {partner_id} actualizado.")
    else:
        print(f"Error al actualizar el contacto {partner_id}")
    return result

def get_category_by_name(name, uid):
    """Busca una categoría (res.partner.category) por su nombre."""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                DATABASE,
                uid,
                PASSWORD,
                'res.partner.category',
                'search_read',
                [[['name', '=', name]]],
                {'fields': ['id', 'name']}
            ]
        },
        "id": 5,
    }
    response = requests.post(ODOO_URL, headers=headers, data=json.dumps(payload))
    result = response.json().get('result')
    if result and len(result) > 0:
        return result[0]
    return None

def create_category(name, uid):
    """Crea una nueva categoría."""
    headers = {'Content-Type': 'application/json'}
    data = {'name': name}
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                DATABASE,
                uid,
                PASSWORD,
                'res.partner.category',
                'create',
                [data]
            ]
        },
        "id": 6,
    }
    response = requests.post(ODOO_URL, headers=headers, data=json.dumps(payload))
    category_id = response.json().get('result')
    if category_id:
        print(f"Categoría '{name}' creada con ID: {category_id}")
    else:
        print(f"Error al crear la categoría '{name}'")
    return category_id

def add_category_to_partner(partner_id, category_id, uid):
    """Agrega una categoría al contacto usando la operación (4, id)."""
    data = {'category_id': [(4, category_id)]}
    return update_partner(partner_id, data, uid)

def normalize_value(field, value):
    """
    Normaliza valores para campos booleanos (forecastbulletin, climabulletin)
    y convierte a cadena en otros casos.
    """
    if field in ["forecastbulletin", "climabulletin"]:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value == 1
        if isinstance(value, str):
            val = value.strip().lower()
            if val in ['true', '1', 'yes']:
                return True
            elif val in ['false', '0', 'no']:
                return False
        return False
    if value is None:
        return ""
    return str(value).strip()

# Mapeo de campos del JSON a los campos de Odoo.
# Se asume que el JSON tiene los campos: name (nombre), last_name, mail (correo), phone_mobile y city.
field_mapping = {
    "firstname": "name",
    "lastname": "last_name",
    "email": "mail",
    "mobile": "phone_mobile",
    "city": "city"
}

def process_contact(json_contact, stats, clima_partners, uid):
    """
    Procesa un contacto:
      - Combina firstname y lastname para formar el 'name'.
      - Busca el contacto por correo; si existe, actualiza los campos diferentes.
      - Si no existe, lo crea.
      - Si el campo 'climabulletin' indica interés, se agrega a la lista para asignar la categoría.
    """
    # Combinar nombre y apellido
    firstname = json_contact.get(field_mapping["firstname"], "")
    lastname = json_contact.get(field_mapping["lastname"], "")
    full_name = f"{firstname} {lastname}".strip() if firstname or lastname else ""
    
    partner_data = {
        'name': full_name if full_name else json_contact.get(field_mapping["email"], "Sin nombre"),
        'email': json_contact.get(field_mapping["email"]),
        'phone': json_contact.get(field_mapping["mobile"]),
        'city': json_contact.get(field_mapping["city"])
    }
    
    email = partner_data.get('email')
    if not email:
        print("No se encontró correo, omitiendo contacto.")
        stats["error"] += 1
        return
    
    # Verificar si el contacto está interesado en el boletín de clima
    interested = normalize_value("climabulletin", json_contact.get("climabulletin"))
    
    existing_partner = get_partner_by_email(email, uid)
    if existing_partner:
        differences = {}
        # Comparar campos para detectar diferencias
        for key in ['name', 'phone', 'city']:
            new_value = partner_data.get(key)
            existing_value = existing_partner.get(key)
            if normalize_value(key, new_value) != normalize_value(key, existing_value):
                differences[key] = new_value
        if differences:
            partner_id = existing_partner.get("id")
            if update_partner(partner_id, differences, uid):
                stats["updated"] += 1
                if interested:
                    clima_partners.append(partner_id)
            else:
                stats["error"] += 1
        else:
            print(f"Contacto con correo {email} ya está actualizado; no se requiere acción.")
            stats["existing"] += 1
            if interested:
                clima_partners.append(existing_partner.get("id"))
    else:
        new_id = create_partner(partner_data, uid)
        if new_id:
            stats["created"] += 1
            if interested:
                clima_partners.append(new_id)
        else:
            stats["error"] += 1

def etl_import_contacts(json_file):
    """
    Función principal ETL:
      - Se conecta a Odoo.
      - Procesa cada contacto del JSON.
      - Al final, asigna la categoría a los contactos interesados.
    """
    stats = {
        "created": 0,
        "updated": 0,
        "existing": 0,
        "error": 0
    }
    clima_partners = []
    uid = odoo_login()
    
    with open(json_file, 'r', encoding='utf-8') as file:
        contacts = json.load(file)
        for contact in contacts:
            process_contact(contact, stats, clima_partners, uid)
    
    print("\nResumen del proceso ETL:")
    print(f"Contactos creados: {stats['created']}")
    print(f"Contactos actualizados: {stats['updated']}")
    print(f"Contactos sin cambios: {stats['existing']}")
    print(f"Contactos con error: {stats['error']}")
    
    # Procesar contactos interesados en el boletín de clima
    if clima_partners:
        tag_name = "Interesados en boletin de clima"
        category = get_category_by_name(tag_name, uid)
        if not category:
            category_id = create_category(tag_name, uid)
        else:
            category_id = category.get("id")
            print(f"La categoría '{tag_name}' ya existe (ID: {category_id}). Se agregarán los contactos.")
        if category_id:
            for partner_id in clima_partners:
                add_category_to_partner(partner_id, category_id, uid)
        else:
            print("No se pudo obtener o crear la categoría.")
    else:
        print("No hay contactos nuevos interesados en el boletín de clima para etiquetar.")

if __name__ == "__main__":
    etl_import_contacts('users.json')
