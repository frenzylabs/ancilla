//
//  printer.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 10/01/19
//  Copyright 2019 Wess Cope
//

import types          from '../actions/types'
import {initialState} from '../state'

export default function(state = initialState, action) {
  switch(action.type) {
    case types.printer.create:
      return state
    case types.printer.list:
      return {...state, printers: action.payload}
    case types.printer.ports:
      return {...state, ports: action.payload.ports || [], baudrates: action.payload['baud_rates'] || []}
    case types.printer.successful:
      return {...state, error: null}
    case types.printer.error:
      return {...state, error: action.payload}
    default:
      return state
  }
}
