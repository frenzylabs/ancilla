//
//  ports.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/30/19
//  Copyright 2019 Wess Cope
//

import Request from './request'

export default {
  list: () => {
    return Request.get('/ports')
  }
}
