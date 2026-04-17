Encrypt: 
tar -czf - tf-deploy | openssl enc -aes-256-cbc -salt -pbkdf2 -iter 100000 -out tf-deploy.tar.gz.enc
Decrypt: 
openssl enc -aes-256-cbc -d -salt -pbkdf2 -iter 100000 -in tf-deploy.tar.gz.enc | tar -xzf -
