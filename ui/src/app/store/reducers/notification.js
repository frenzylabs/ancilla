//
//  notification.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 10/02/19
//  Copyright 2019 Wess Cope
//

import types          from '../actions/types'
import {initialState} from '../state'

export default function(state = initialState, action) {
  if(!action.type.includes("NOTIFICATION")) { return state }

  switch(action.type) {
    case types.notification.dismiss:
      return {
        ...state,
        notification: null
      }
    default:
      return {
        ...state,
        notification: action
      }      
  }
}
