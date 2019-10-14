//
//  connection.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 10/14/19
//  Copyright 2019 Wess Cope
//

import {Connection} from '../network'

export default class ConnectionProvider {
  constructor() {
    this.registry = []
  }

  get(conn) {
    let mapped = this.registry.filter(item => { return item.name == conn.name })
    
    
    if(mapped.length > 0) { 
      return mapped[0]
    }

    let _conn = new Connection(conn)
    this.registry.push(_conn)

    return _conn
  }

  remove(conn) {
    this.registry.filter(item => { return item.name == conn.name}).forEach(item => {
      item.disconnect()
      del(item)
    })
  }
}
