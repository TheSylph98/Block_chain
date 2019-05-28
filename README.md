# Block_chain
+ Cài đặt yêu cầu Python 3.6 và Flask + request
   pip install Flask==0.12.2 requests==2.18.4 
   
 + Khởi tạo các node:
  - python blockchain.py
  - python blockchain.py --port 5001
  - python blockchain.py --port 5002
  ...
 + API của chương trình
  - nodes/register: đăng ký các node vừa khởi tạo vào mạng Blockchain
  - mine: để đào coin :v 
  - chain : trả lại chuỗi block chain
  - transactions/new: tạo giao dịch mới 
  - nodes/resolve: giải quyết xung đột, bằng POW
