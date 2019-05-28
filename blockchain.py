import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request,render_template


class Blockchain:
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()

        # khởi tạo 1 block ban đầu
        self.new_block(previous_hash='1', proof=10)

    def new_block(self, proof, previous_hash):
        """
        Tạo 1 block mới trong blockchain
        :param proof: độ công nhận theo POW
        :param previous_hash: Hash of previous Block
        :return: New Block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
            #'hash': self.hash(block),
        }

        # Reset giao dịch hiện tại
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """
        tạo 1 giao dịch mới
        :param sender: Address of the Sender
        :param recipient: Address of the Recipient
        :param amount: Số tiền
        :return: Chỉ số của khối giữ giao dịch này
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

    @property
    def last_block(self):
        # trả lại block cuối của chuỗi blockchain
        return self.chain[-1]

    @staticmethod
    def hash(block):
        """
        Mã hóa 1 SHA-256 Block
        :param block: Block
        """
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def valid_chain(self, chain):
        """
        Kiểm tra 1 chain có hợp lệ hay không
        :param chain: 1 blockchain
        :return: True if valid, False if not
        """
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n----------------------------\n")
            # check hash of block
            last_block_hash = self.hash(last_block)
            if block['previous_hash'] != last_block_hash:
                return False

            # Check POW
            if not self.valid_proof(last_block['proof'], block['proof'], last_block_hash):
                return False

            last_block = block
            current_index += 1

        return True

    def proof_of_work(self, last_block):
        """
        thuật toán POW cơ bản với difficult = 4 :
        - Tìm một số p' sao cho hash (pp') chứa 4 số 0 đứng đầu
        - Trong đó p là  proof_of_work của block trước đó
        :param last_block: <dict> last Block
        :return: <int>
        """
        last_proof = last_block['proof']
        last_hash = self.hash(last_block)

        proof = 0
        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof, last_hash):
        """
        xác thực bằng chứng
        hash(pp') chứa 4 số 0 ở đầu
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :param last_hash: <str> hash of the Previous Block
        :return: <bool>
        """
        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def register_node(self, address):
        """
        Thêm 1 node vào vào mạng
        :param address: Address of node. (e.g: http://127.0.0.1:5001')
        """
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')

    def resolve_conflicts(self):
        """
        Kiểm tra các node trong mạng có hợp lệ hay không
        Nếu 1 chain hợp lệ và dài hơn chain hiện tại
        thì nó sẽ thay thế chain hiện tại -- thuật toán Consensus
        :return: True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # Tìm chuỗi dài hơn chuỗi hiên tại
        max_length = len(self.chain)

        # lấy và xác minh chuỗi từ tất cả các node trong mạng
        for node in neighbours:
            response = requests.get(f'http://{node}/chain1')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check chuỗi dài hơn chuỗi hiện tại
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # thay thế chuỗi mới tìm đk cho chuỗi hiện tại
        if new_chain:
            self.chain = new_chain
            return True

        return False


#--------------------------------------------------------------------------------------#
#Server
# Cài đặt các API
app = Flask(__name__)

# Tạo biến tổng quát địa chỉ duy nhất cho node
node_identifier = str(uuid4()).replace('-', '')

# Khởi tạo Blockchain
blockchain = Blockchain()

@app.route("/home")
def home():
    return render_template('home.html')
    
@app.route("/")
@app.route('/mine', methods=['GET'])
def mine():
    # Chạy POW để có được proof tiếp theo
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_block)

    # Sender "0" biểu thị node này khai thác 1 coin mới .
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # Tạo 1 khối mới bằng cách thêm vào chuỗi
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)
    block_hash = blockchain.hash(block)

    response = {
        'message': "Mind a New Block",
        'index': block['index'],
        'hash': block_hash,
        'timestamp': block['timestamp'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],

    }
    # return jsonify(response), 200
    return render_template('mine.html',response=response)

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    if request.method == 'POST':
        if (request.form['sender'] and request.form['recipient']) and request.form['amount']:
            sender = request.form['sender']
            recipient = request.form['recipient']
            amount = request.form['amount']

            index = blockchain.new_transaction(sender,recipient,amount)

            response = {'message': f'Giao dịch sẽ được thêm vào Block{index}',
                        'chain': blockchain.chain,
                        'length': len(blockchain.chain),
                        }
            return render_template('chain.html', res=response)
        else:
            return 'Missing values', 400

@app.route('/transactions/new', methods=['GET'])
def new_trans():
    return render_template('addtrans.html')

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return render_template('chain.html',res=response)

@app.route('/chain1', methods=['GET'])
def full_chain_1():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    if request.method == 'POST':
        nodes = request.form['node']
        if nodes is None:
            return "Error: Hãy cung cấp chuỗi hợp lệ!", 400

        #for node in nodes:
        blockchain.register_node(nodes)

        response = {
           'message': 'Node mới được thêm vào',
           'total_nodes': list(blockchain.nodes)
                   }
        return render_template('list_nodes.html',res=response)
        # return jsonify(response), 200

@app.route('/nodes/register', methods=['GET'])
def regis_node():
    return render_template('register_node.html')

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Chuỗi đã được thay thế',
            'chain': blockchain.chain,
            'length': len(blockchain.chain)
        }
    else:
        response = {
            'message': 'Blockchain: ',
            'chain': blockchain.chain,
             'length': len(blockchain.chain)
        }

    # return jsonify(response), 200
    return render_template('chain.html',res=response)

# main
if __name__ == '__main__':
    # app.run(debug=True)
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('--port', default=5000, type=int )
    args = parser.parse_args()
    port = args.port

    app.run(host='127.0.0.1', port=port)

