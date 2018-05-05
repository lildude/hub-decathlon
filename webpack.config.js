var path = require("path")
var webpack = require('webpack')
var BundleTracker = require('webpack-bundle-tracker')

module.exports = {
  context: __dirname,

  entry: {
      aerobiaConfig: './tapiriik/frontend/aerobia-config',
  },

  output: {
      path: path.resolve('./tapiriik/web/static/js/bundles/'),
      filename: "[name].js"
  },

  plugins: [
    new BundleTracker({filename: './webpack-stats.json'}),
    new webpack.HotModuleReplacementPlugin()
  ],

  module: {
    rules: [
        { 
            test: /\.jsx?$/, 
            exclude: /node_modules/, 
            use: ['babel-loader']
        },
    ],
  },

  resolve: {
    modules: ['node_modules'],
    extensions: ['.js', '.jsx']
  }
}