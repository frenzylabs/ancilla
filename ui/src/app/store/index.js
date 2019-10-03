//
//  index.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 10/01/19
//  Copyright 2019 Wess Cope
//

import {
  createStore,
  applyMiddleware
} from 'redux'

import thunk      from 'redux-thunk'
import reducer    from './reducers'

const store = createStore(
  reducer, 
  applyMiddleware(thunk)
)

window.store = store

export default store
