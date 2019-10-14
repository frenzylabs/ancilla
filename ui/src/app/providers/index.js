//
//  index.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 10/14/19
//  Copyright 2019 Wess Cope
//

import ConnectionProvider from './connection'

const Providers = {
  connection: new ConnectionProvider()
}

window.providers = Providers

export default Providers
