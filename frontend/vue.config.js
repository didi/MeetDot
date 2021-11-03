const dotenv = require("dotenv");
const dotenvExpand = require("dotenv-expand");
var myEnv = dotenv.config({ path: "../.env" });
dotenvExpand(myEnv);

let credentials;
let certificate_url;

////// Configuration for HTTPS //////
// Try to load certfile
try {
  const fs = require("fs");
  credentials = {
    // Note: EOENT errors here are fine if you're developing locally
    // TODO: Figure out how to suppress them
    key: fs.readFileSync(process.env.SSL_CERT_PATH + "privkey.pem"),
    cert: fs.readFileSync(process.env.SSL_CERT_PATH + "cert.pem"),
    https: true,
  };
  certificate_url = process.env.HOSTNAME; // url that the certificate is assigned to
  // If you get "Invalid Host header", make sure this is properly set
} catch (err) {
  console.error(`Cert file does not exist, frontend will be served over HTTP.
        If you are developing locally, this is fine.
        Otherwise see "security notes" in the readme`);
  console.error(err);
  credentials = {};
  certificate_url = undefined;
}

module.exports = {
  devServer: {
    ...credentials,
    public: certificate_url,
    watchOptions: {
      ignored: /node_modules/,
    },
  },
  pages: {
    index: {
      title: "MeetDot",
      entry: "src/main.js",
    },
  },
};
