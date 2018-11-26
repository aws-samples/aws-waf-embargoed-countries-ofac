#!/bin/bash
#--------------------------------------------------------------------------------------------------
# This assumes all of the OS-level configuration has been completed and git repo has already
# been cloned. Other than that, this script should be run from the repo's deployment directory.
# To run it, just execute the following commands:
#
# cd deployment
# ./build-s3-dist.sh source-bucket-base-name source-bucket-key-prefix version
#
# Where:
#   - source-bucket-base-name: name for the S3 bucket location
#   - source-bucket-key-prefix: folder prefix path inside the bucket
#   - version: also used to compose where the template will source the Lambda code from
#
# For example: ./build-s3-dist.sh awsiammedia public/sample/aws-waf-embargoed-countries-ofac v1.0
#
# The template will then expect the source code to be located in:
#   - bucket:  awsiammedia
#   - key prefix: public/sample/aws-waf-embargoed-countries-ofac/v1.0/
#--------------------------------------------------------------------------------------------------

# Check to see if input has been provided:
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Please provide the base source bucket name and version where the lambda code will eventually reside."
    echo "For example: ./build-s3-dist.sh solutions v1.0.0"
    exit 1
fi

# Get reference for all important folders
template_dir="$PWD"
dist_dir="$template_dir/dist"
source_dir="$template_dir/../source"

echo "------------------------------------------------------------------------------"
echo "[Init] Clean old dist folder"
echo "------------------------------------------------------------------------------"
echo "rm -rf $dist_dir"
rm -rf "$dist_dir"
echo "find $source_dir -type f -name 'package-lock.json' -delete"
find $source_dir -type f -name 'package-lock.json' -delete
echo "find $source_dir -type f -name '.DS_Store' -delete"
find $source_dir -type f -name '.DS_Store' -delete
echo "mkdir -p $dist_dir"
mkdir -p "$dist_dir"
echo ""
echo "------------------------------------------------------------------------------"
echo "[Packing] Main Template"
echo "------------------------------------------------------------------------------"
echo "cp -f $template_dir/aws-waf-embargoed-countries-ofac.template $dist_dir"
cp -f $template_dir/aws-waf-embargoed-countries-ofac.template $dist_dir
echo ""
echo "Updating code source bucket in template with $1"
replace="s#%%BUCKET_NAME%%#$1#g"
echo "sed -i '' -e $replace $dist_dir/aws-waf-embargoed-countries-ofac.template"
sed -i '' -e $replace $dist_dir/aws-waf-embargoed-countries-ofac.template
echo ""
echo "Updating code source bucket in template with $2"
replace="s#%%BUCKET_KEY_PREFIX%%#$2#g"
echo "sed -i '' -e $replace $dist_dir/aws-waf-embargoed-countries-ofac.template"
sed -i '' -e $replace $dist_dir/aws-waf-embargoed-countries-ofac.template
echo ""
echo "Updating code source version in template with $3"
replace="s#%%VERSION%%#$3#g"
echo "sed -i '' -e $replace $dist_dir/aws-waf-embargoed-countries-ofac.template"
sed -i '' -e $replace $dist_dir/aws-waf-embargoed-countries-ofac.template
echo ""
echo "------------------------------------------------------------------------------"
echo "[Packing] ALB Template"
echo "------------------------------------------------------------------------------"
echo "cp -f $template_dir/aws-waf-embargoed-countries-ofac-alb.template $dist_dir"
cp -f $template_dir/aws-waf-embargoed-countries-ofac-alb.template $dist_dir
echo "Updating code source bucket in template with $1"
replace="s#%%BUCKET_NAME%%#$1#g"
echo "sed -i '' -e $replace $dist_dir/aws-waf-embargoed-countries-ofac-alb.template"
sed -i '' -e $replace $dist_dir/aws-waf-embargoed-countries-ofac-alb.template
echo ""
echo "Updating code source bucket in template with $2"
replace="s#%%BUCKET_KEY_PREFIX%%#$2#g"
echo "sed -i '' -e $replace $dist_dir/aws-waf-embargoed-countries-ofac-alb.template"
sed -i '' -e $replace $dist_dir/aws-waf-embargoed-countries-ofac-alb.template
echo ""
echo "Updating code source version in template with $3"
replace="s#%%VERSION%%#$3#g"
echo "sed -i '' -e $replace $dist_dir/aws-waf-embargoed-countries-ofac-alb.template"
sed -i '' -e $replace $dist_dir/aws-waf-embargoed-countries-ofac-alb.template
echo ""
echo "------------------------------------------------------------------------------"
echo "[Packing] CloudFront Template"
echo "------------------------------------------------------------------------------"
echo "cp -f $template_dir/aws-waf-embargoed-countries-ofac-cloudfront.template $dist_dir"
cp -f $template_dir/aws-waf-embargoed-countries-ofac-cloudfront.template $dist_dir
echo "Updating code source bucket in template with $1"
replace="s#%%BUCKET_NAME%%#$1#g"
echo "sed -i '' -e $replace $dist_dir/aws-waf-embargoed-countries-ofac-cloudfront.template"
sed -i '' -e $replace $dist_dir/aws-waf-embargoed-countries-ofac-cloudfront.template
echo ""
echo "Updating code source bucket in template with $2"
replace="s#%%BUCKET_KEY_PREFIX%%#$2#g"
echo "sed -i '' -e $replace $dist_dir/aws-waf-embargoed-countries-ofac-cloudfront.template"
sed -i '' -e $replace $dist_dir/aws-waf-embargoed-countries-ofac-cloudfront.template
echo ""
echo "Updating version in template with $3"
echo "Updating code source version in template with $3"
replace="s#%%VERSION%%#$3#g"
echo "sed -i '' -e $replace $dist_dir/aws-waf-embargoed-countries-ofac-cloudfront.template"
sed -i '' -e $replace $dist_dir/aws-waf-embargoed-countries-ofac-cloudfront.template
echo ""
echo "------------------------------------------------------------------------------"
echo "[Packing] Resources"
echo "------------------------------------------------------------------------------"
echo "cp -f $source_dir/resources/embargoed-countries.json $dist_dir/"
cp -f $source_dir/resources/embargoed-countries.json $dist_dir/
echo ""
echo "------------------------------------------------------------------------------"
echo "[Packing] Threat Feed"
echo "------------------------------------------------------------------------------"
cd $source_dir/custom-resource
zip -q -r9 $dist_dir/custom-resource.zip *
echo ""
echo "------------------------------------------------------------------------------"
echo "[Packing] Embargoed Countries Parser"
echo "------------------------------------------------------------------------------"
cd $source_dir/embargoed-countries-parser
zip -q -r9 $dist_dir/embargoed-countries-parser.zip *
echo ""
cd $template_dir