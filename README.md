# matthewtrost.com

Static homepage for `matthewtrost.com` and `www.matthewtrost.com`.

## Structure

- `site/`: static files deployed to S3
- `infra/site.yml`: CloudFormation for S3, ACM, CloudFront, Route53, and GitHub OIDC
- `.github/workflows/deploy.yml`: deploys `site/` on pushes to `main`

## Deploy

AWS is provisioned from `infra/site.yml` in `us-east-1`. GitHub Actions assumes an AWS role with OIDC and syncs `site/` to S3, then invalidates CloudFront.

## License

See `LICENSE`.
