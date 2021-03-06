from flask_restful import Resource, reqparse
from flask_api import status
from models import *
from flask_jwt_extended import jwt_required, get_jwt_identity
import datetime

parser = reqparse.RequestParser()
parser_args = ['id_fila', 'nome', 'horario_abertura', 'horario_fechamento',
               'tempo_espera_indicado', 'descricao', 'estabelecimento_id']
for i in parser_args:
    parser.add_argument(i)
parser.add_argument('usar_tempo_gerado', type=bool)

def get_pos_usuario(id_cliente, id_fila): #todo mover para utils
    posicao_absoluta_cliente = db.session.query(ClienteFilas).filter_by(id_cliente=id_cliente, id_fila=id_fila).first()
    if posicao_absoluta_cliente:
        posicao_absoluta_cliente = posicao_absoluta_cliente.posicao_absoluta
    else:
        return 0
    clientes_filas = db.session.query(ClienteFilas).filter_by(id_fila=id_fila).all()
    
    cont_pos = 0
    for j in clientes_filas:
        if j.posicao_absoluta < posicao_absoluta_cliente:
            cont_pos += 1
    return cont_pos

class cliente_fila(Resource):
    @jwt_required
    def post(self):
        data = parser.parse_args()
        fila = db.session.query(Fila).filter_by(id=int(data['id_fila'])).first()
        user = User.find_by_username(get_jwt_identity())
        print(user.id)
        if fila.id != int(data['id_fila']):
            return {
                'message': 'A fila na qual você tentou se inscrever deixou de existir',
            }, 200
        if not fila:
            return {
                'message': 'Fila inexistente.'
            }, 500
        print(user.is_cliente)
        if user.is_cliente == 1: #and datetime.now().time() < fila.horario_abertura:
            print("entrou")
            if len(db.session.query(ClienteFilas).filter_by(id_cliente=user.cliente.id, id_fila=fila.id).all()) == 0:
                #user.cliente.filas.append(fila)
                tempo_espera_atual = 0
                if fila.usar_tempo_gerado:
                    tempo_espera_atual = len(fila.cliente_filas) * fila.tempo_espera_gerado
                    # hora entrada = default
                else:
                    tempo_espera_atual = len(fila.cliente_filas) * fila.tempo_espera_indicado
                #db.session.add(user)
                fila.ultima_posicao = fila.ultima_posicao + 1
                relation = ClienteFilas(id_cliente=user.cliente.id, id_fila=fila.id, posicao_absoluta=fila.ultima_posicao + 1)
                posicao_rel = len(fila.cliente_filas)
                db.session.add(relation)
                db.session.add(fila)
                db.session.commit()
                return {
                    'message': 'Inscrito com sucesso!',
                    'posicao': posicao_rel,
                    'tempo_espera_atual': tempo_espera_atual
                }, 500
            else:
                return {
                    'message': 'Você já está inscrito nessa fila!',
                }, 500
        else:
            return {
                'message': 'Operação não permitida.'
            }, 403

    @jwt_required
    def get(self):
        data = parser.parse_args()
        user = User.find_by_username(get_jwt_identity())
        filas = user.cliente.cliente_filas
        filas_final = []
        
        for i in filas:
            print("entrou")
            posicao = get_pos_usuario(user.cliente.id, i.id)

            tempo_espera_atual = 0
            
            if i.filas.usar_tempo_gerado:
                tempo_espera_atual = i.filas.tempo_espera_gerado * posicao
            else:
                tempo_espera_atual = i.filas.tempo_espera_indicado * posicao

            filas_final.append({
                'id_fila': i.filas.id,
                'nome': i.filas.nome,
                'qtd_pessoas': len(db.session.query(ClienteFilas).filter_by(id_fila=i.filas.id).all()),
                'tempo_espera_atual': tempo_espera_atual,
                'estabelecimento': i.filas.estabelecimento.nome,
                'posicao': posicao,
            })
        return {
            'filas:': filas_final
        }, 200
        #todo delete

    @jwt_required
    def delete(self):
        data = parser.parse_args()
        user = User.find_by_username(get_jwt_identity())
        if user.is_cliente:
            cliente = user.cliente
            fila = db.session.query(Fila).filter_by(id=int(data['id_fila'])).first()
            busca = db.session.query(ClienteFilas).filter_by(id_cliente=user.cliente.id, id_fila=fila.id).first()
            if not busca:
                return {
                    'message': 'Operação não permitida'
                }, 403
            db.session.delete(busca)
            db.session.commit()
            return {
                'message': 'Inscrição apagada!'
            }, 200
        else:
            return {
               'message': 'Operação não permitida'
            }, 403

class crud_fila(Resource):
    @jwt_required
    def post(self):
        data = parser.parse_args()
        user = User.find_by_username(get_jwt_identity())
        print(user.is_cliente)
        if not user.is_cliente:
            estab = user.estabelecimento
            print("estab nome:", estab.nome)
            h, m = map(int, data['horario_abertura'].split(':'))
            horario_abertura = datetime.time(hour=h, minute=m)
            h, m = map(int, data['horario_fechamento'].split(':'))
            horario_fechamento = datetime.time(hour=h, minute=m)


            fila = Fila(
                nome=data['nome'],
                descricao=data['descricao'],
                horario_abertura=horario_abertura,
                horario_fechamento=horario_fechamento,
                tempo_espera_indicado=data['tempo_espera_indicado'],
                tempo_espera_gerado=data['tempo_espera_indicado'],
                usar_tempo_gerado=data['usar_tempo_gerado']
            )

            estab.filas.append(fila)
            db.session.add(fila)
            db.session.add(estab)
            db.session.commit()
            return {
                'message': 'Fila criada com sucesso'
            }, 200
        else:
            return {
                'message': 'Operação não permitida.'
            }, 403

    @jwt_required
    def get(self): 
        data = parser.parse_args()
        filas = []
        print(data['estabelecimento_id'])
        if data['id_fila'] is not None:
            filas = db.session.query(Fila).filter_by(id=int(data['id_fila'])).all()
        elif data['estabelecimento_id'] is not None:
            filas = db.session.query(Fila).filter_by(estabelecimento_id=int(data['estabelecimento_id'])).all()
        else:
            filas = db.session.query(Fila).all()
        f = []
        print(len(filas))
        for i in filas:
            tempo_espera = 0
            if i.usar_tempo_gerado:
                tempo_espera = i.tempo_espera_gerado
            else:
                tempo_espera = i.tempo_espera_indicado
            f.append(
                {
                    'id_fila': i.id,
                    'qtd_pessoas': len(db.session.query(ClienteFilas).filter_by(id_fila=i.filas.id).all()),
                    'tempo_espera_atual': (len(i.clientes) * tempo_espera),
                    'nome': i.nome,
                    'descricao': i.descricao,
                    'estabelecimento_id': i.estabelecimento_id,
                    'nome_estabelecimento': i.estabelecimento.nome
                }
            )
        return {
                'filas': f
            }, 200

    @jwt_required
    def delete(self):
        data = parser.parse_args()
        user = User.find_by_username(get_jwt_identity())
        if not user.is_cliente:
            estab = user.estabelecimento
            fila = db.session.query(Fila).filter_by(id=int(data['id_fila'])).first()
            if fila not in estab.filas:
                return {
                           'message': 'Operação não permitida'
                    }, 403
            estab.filas.remove(fila)
            for i in fila.clientes: #todo: verificar cascade sqlalchemy
                i.filas.remove(fila)
                db.session.add(i)
                #todo notificação: fila removida
            db.session.add(estab)
            db.session.delete(fila)
            db.session.commit()
            return {
                'message': 'Fila apagada!'
            }, 200
        else:
            return {
                'message': 'Operação não permitida'
            }, 403

class visualizar_ordem_fila(Resource):
    @jwt_required
    def get(self):
        data = parser.parse_args()
        filter_ = (data['id_fila'])
        filas = []
        if filter_:
            filas = db.session.query(Fila).filter_by(id=int(filter_)).all()
        else:
            filas = db.session.query(Fila).all()
        f = []
        for i in filas:
            tempo_espera = 0
            if i.usar_tempo_gerado:
                tempo_espera = i.tempo_espera_gerado
            else:
                tempo_espera = i.tempo_espera_indicado
            clientes = []
            for j in i.cliente_filas: #todo O(n^2) pode virar O(n) com counting sort #todo otimizar queries
                clientes.append(
                    {
                        'posicao': get_pos_usuario(j.clientes.id, i.id),
                        'id_cliente': j.clientes.id,
                        'nome_cliente': j.clientes.nome_completo
                    }
                )
            f.append(
                {
                    'id_fila': i.id,
                    'qtd_pessoas': len(db.session.query(ClienteFilas).filter_by(id_fila=i.id).all()),
                    'tempo_espera_atual': (len(db.session.query(ClienteFilas).filter_by(id_fila=i.id).all()) * tempo_espera),
                    'nome': i.nome,
                    'descricao': i.descricao,
                    'estabelecimento_id': i.estabelecimento_id,
                    'nome_estabelecimento': i.estabelecimento.nome,
                    'clientes': clientes
                }
            )
            return {
                'filas': f
            }, 200

class prox_da_fila(Resource):
    @jwt_required
    def get(self):
        data = parser.parse_args()
        filas = []
        if (data['id_fila']):
            fila = db.session.query(Fila).filter_by(id=int((data['id_fila']))).first()
            for j in fila.cliente_filas: #todo O(n^2) pode virar O(n) com counting sort #todo otimizar queries
                if get_pos_usuario(j.id, (data['id_fila'])) == 0:
                    return {
                        'nome_completo': j.clientes.nome_completo,
                        'id_cliente': j.id
                    }, 200
            return {
                       'nome_completo': 'Não há espera',
                       'id_cliente': None
                   }, 200
        else:
            return {
                'message': 'ID da fila faltante.'
            }, 400

#todo visualizar posição em fila: posicao_atual - clientes atendidos #done
#todo estabelecimento adiciona pessoa #done
#todo get tempo_espera_fila #done
#todo visualizar: proximo da fila, todas pessoas #done
#todo get estabelecimento por categoria #done

#todo cliente entrou, cliente saiu, cliente faltou #todo
#todo edit estabelecimento


class api_estabelecimento(Resource):
    @jwt_required
    def get(self):
        data = parser.parse_args()
        estabs = []
        categoria_id = data['categoria_id']
        id_estabelecimento = data['id_estabelecimento']
        if categoria_id:
            estabs = db.session.query(categoria_id=categoria_id).all()
        elif id_estabelecimento:
            estabs = db.session.query(id=id_estabelecimento).first()
        else:
            estabs = db.session.query().all()
        result = []
        for i in estabs:
            result.append({
                'id_estabelecimento': i.id,
                'categoria_id': i.categoria_id,
                'endereco': i.endereco,
                'cep': i.cep,
                'nome': i.nome,
                'horario_abertura': i.horario_abertura,
                'horario_fechamento': i.horario_fechamento
            })
        return {
            'estabelecimentos': result
        }, 200
    
class operacao_fila(Resource):
    @jwt_required
    def post(self):
        data = parser.parse_args()
        id = int(data['id_fila'])
        fila = db.session.query(Fila).filter_by(id=id).first()
        print(fila.nome)
        fila = db.session.query(Fila).filter_by(id=int((data['id_fila']))).first()
        for j in fila.cliente_filas:  # todo O(n^2) pode virar O(n) com counting sort #todo otimizar queries
            if get_pos_usuario(j.id, (data['id_fila'])) == 0:
                pos_fila = db.session.query(ClienteFilas).filter_by(id_cliente=j.clientes.id, id_fila=id).first()
                try:
                    db.session.delete(pos_fila)
                    db.session.commit()
                except:
                    return {
                            'message': 'Fila vazia'
                        }, 200
                return {
                    'message': 'Atendimento registrado'
                }, 200
        return {
            'message': 'Erro'
            }, 500

    ''' @jwt_required
    def put(self):
        data = parser.parse_args()
        id = int(data['id'])
        
        return {
            'message': 'Dados editados com sucesso'
        }
        '''

   # @jwt_required
