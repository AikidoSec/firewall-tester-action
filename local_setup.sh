

# mkdir zen-demo
mkdir -p zen-demo

cd zen-demo

git clone  --recursive -b dev-testing https://github.com/Aikido-demo-apps/zen-demo-nodejs.git zen-demo-nodejs
git clone  --recursive -b gunicorn-threads-1w-4t https://github.com/Aikido-demo-apps/zen-demo-python.git zen-demo-python
git clone  --recursive -b dev-testing https://github.com/Aikido-demo-apps/zen-demo-php.git zen-demo-php
git clone  --recursive -b fix-qa-endpoints https://github.com/Aikido-demo-apps/zen-demo-dotnet-core.git zen-demo-dotnet-core
git clone  --recursive -b dev-testing https://github.com/Aikido-demo-apps/zen-demo-java.git zen-demo-java
git clone  --recursive -b dev-testing https://github.com/Aikido-demo-apps/zen-demo-ruby.git zen-demo-ruby
git clone  --recursive -b main https://github.com/Aikido-demo-apps/zen-demo-go.git zen-demo-go

