//
//  printer.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 10/01/19
//  Copyright 2019 Wess Cope
//

import types      from './types'

export default {
  list: (items) => {
    return {
      type:     types.printer.list,
      payload:  items
    }
  }
}
