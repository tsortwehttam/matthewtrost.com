# matthewtrost.com

Static homepage for `matthewtrost.com` and `www.matthewtrost.com`.

## Structure

- `site/`: static files deployed to S3
- `site/rirekisho.html`: Japanese résumé page; private application fields are edited directly on the document before printing
- `site/rirekisho-fillable.pdf`: offline fillable A4 version of the same résumé
- `infra/site.yml`: CloudFormation for S3, ACM, CloudFront, Route53, and GitHub OIDC
- `.github/workflows/deploy.yml`: deploys `site/` on pushes to `main`

## Deploy

AWS is provisioned from `infra/site.yml` in `us-east-1`. GitHub Actions assumes an AWS role with OIDC and syncs `site/` to S3, then invalidates CloudFront.

## Local

Run `yarn dev`, then open `http://localhost:3000`.

To rebuild the fillable PDF after editing the résumé, run `python3 scripts/build_rirekisho_pdf.py` with Chrome, `fonttools`, `pypdf`, and `reportlab` installed. The build embeds [Noto Sans JP](https://github.com/google/fonts/tree/main/ofl/notosansjp) (OFL) for Japanese form entries.

## License

See `LICENSE`.
