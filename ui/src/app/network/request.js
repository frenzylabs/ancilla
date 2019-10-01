//
//  request.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/30/19
//  Copyright 2019 Wess Cope
//

import axios from 'axios'

const Request = axios.create({
  baseURL: 'http://localhost:5000',
  responseType: 'json',
  headers: {
    'Content-Type'      : 'application/json',
    'Accept'            : 'application/json',
    'X-Requested-With'  : 'XMLHttpRequest',
    'Access-Control-Allow-Origin' : '*'
  }
})




export default Request
