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
        self.new_block(previous_hash='1', proof=100)

    def register_node(self, address):
        """
        Thêm 1 node vào list node
        :param address: Address of node.
        """

        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')

    def valid_chain(self, chain):
        """
        xác nhận tính hợp lệ 1 block chain
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

    def resolve_conflicts(self):
        """
        Đây là thuật toán đồng thuận,
        nó giải quyết xung đột bằng cách
        thay thế chuỗi của chúng tôi bằng chuỗi dài nhất trong mạng.

        :return: True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # Tìm chuỗi dài hơn chuỗi hiên tại
        max_length = len(self.chain)

        # lấy và xác minh chuỗi từ tất cả các node trong mạng
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

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

    def proof_of_work(self, last_block):
        """
        thuật toán POW cơ bản:

        - Tìm một số p' sao cho hàm băm (pp') chứa 4 số 0 đứng đầu
        - Trong đó p là bằng chứng trước đó và p' là bằng chứng mới

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

        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :param last_hash: <str> hash of the Previous Block
        :return: <bool>

        """

        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


# Cài đặt các API
app = Flask(__name__)

# Tạo biến tổng quát địa chỉ duy nhất cho node
node_identifier = str(uuid4()).replace('-', '')

# Khởi tạo Blockchain
blockchain = Blockchain()
@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html")

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

    response = {
        'message': "New Block",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],

    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check các trường bắt buộc có trong dữ liệu pg thức POST
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Tạo 1 giao dịch mới
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Giao dịch sẽ được thêm vào Block{index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Hãy cung cấp chuỗi hợp lệ!", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'Node mới được thêm vào',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Chuỗi đã được thay thế',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Chuỗi có thẩm quyền',
            'chain': blockchain.chain
        }

    return jsonify(response), 200

# main
if __name__ == '__main__':
    # app.run(debug=True)
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='127.0.0.1', port=port)

