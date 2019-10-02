//
//  index.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 10/01/19
//  Copyright 2019 Wess Cope
//

import {combineReducers}  from 'redux'
import printer            from './printer'
import notification       from './notification'

export default combineReducers({
  printer,
  notification
})
