## AWS Waf Embargoed Countries Ofac

The article provides a push-button solution to protect your infrastructure against incoming traffic from embargoed countries as defined by OFAC.

## Authors
[Heitor Vital](https://github.com/hvital) & [Rajat Ravinder Varuni](https://github.com/varunirv)
 
## Building Lambda Package
```bash
cd deployment
./build-s3-dist.sh source-bucket-base-name source-bucket-key-prefix version
```

Where:
 - source-bucket-base-name: name for the S3 bucket location
 - source-bucket-key-prefix: folder prefix path inside the bucket
 - version: also used to compose where the template will source the Lambda code from

For example: ./build-s3-dist.sh awsiammedia public/sample/aws-waf-embargoed-countries-ofac v1.0
The template will then expect the source code to be located in:
 - bucket: awsiammedia
 - key prefix: public/sample/aws-waf-embargoed-countries-ofac/v1.0/

## CF template and Lambda function
Located in deployment/dist


## License Summary

This sample code is made available under a modified MIT license. See the LICENSE file.
