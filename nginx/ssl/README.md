# SSL Certificates for NGINX

This directory should contain your Cloudflare Origin Certificate files:

1. `certificate.pem` - The Origin Certificate from Cloudflare
2. `private.key` - The Private Key generated with the certificate

## How to Generate Cloudflare Origin Certificates

1. Log in to your Cloudflare dashboard
2. Go to SSL/TLS > Origin Server
3. Click "Create Certificate"
4. Select:
   - RSA (2048) as the private key type
   - Hostnames: `api.dao.cafe` and `dao.cafe`
   - Validity: 15 years (maximum)
5. Click "Create"
6. Cloudflare will generate two files:
   - Origin Certificate (save as `certificate.pem` in this directory)
   - Private Key (save as `private.key` in this directory)

## Security Notice

- Keep your private key secure and never commit it to version control
- Ensure file permissions are set correctly (readable only by the NGINX process)
- Consider using Docker secrets or a secure vault for production environments
