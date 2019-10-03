//
//  connection.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 10/03/19
//  Copyright 2019 Wess Cope
//

import types from './types'

export default {
  connect: (name, port, path, baudrate) => {
    return {
      type:     types.connection.connect,
      payload:  {name, port, path, baudrate}
    }
  },

  connected: (connection) => {
    return {
      type:     types.connection.connected,
      payload:  connection
    }
  },

  disconnected: (connection) => {
    return {
      type:     types.connection.disconnected,
      payload:  connection
    }
  },

  receive:(connection, msg) => {
    return {
      type:     types.connection.received,
      payload:  {connection, msg}
    }
  }
}
