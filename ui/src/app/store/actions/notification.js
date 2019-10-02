//
//  notification.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 10/02/19
//  Copyright 2019 Wess Cope
//

import types from './types'

export default {
  info: (msg) => {
    return {
      type:     types.notification.info,
      payload:  msg
    }
  },

  success: (msg) => {
    return {
      type:     types.notification.success,
      payload:  msg
    }
  },

  warning: (msg) => {
    return {
      type:     types.notification.warning,
      payload:  msg
    }
  },

  failure: (msg) => {
    return {
      type:     types.notification.failure,
      payload:  msg
    }
  },

  dismiss: () => {
    return {
      type: types.notification.dismiss
    }
  }
}
