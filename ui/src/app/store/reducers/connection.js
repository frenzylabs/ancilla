//
//  buffer.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 10/03/19
//  Copyright 2019 Wess Cope
//

import types          from '../actions/types'
import {initialState} from '../state'
import {Connection}   from '../../network'

export default function(state = initialState, action) {
  if(!action.type.includes("SOCKET.")) { return state }

  switch(action.type) {
    case types.connection.connect:
      const _conn = new Connection(action.payload)
      _conn.connect()

      return {
        ...state,
        currentConnection: _conn
      }

    case types.connection.connected:
      return {
        ...state,
        connections: state.connections.concat([action.payload])
      }
    
    case types.connection.disconnected:
      return {
        ...state,
        connections: state.connections.filter((item) => {item.port != action.payload.port})
      }
  
    default:
      return state
  }
}
