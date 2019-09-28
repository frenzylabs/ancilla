//
//  list.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/27/19
//  Copyright 2019 Wess Cope
//

import React from 'react'

import {
  Menu,
  Header
} from 'semantic-ui-react'

import NewConnectionModal from './new/modal'

export default class ConnectionList extends React.Component {
  render() {
    return (
      <Menu.Item>
          <Menu.Header>
            <Menu secondary compact>
              <Menu.Item position='left' style={{padding: 0}}>
                <Header textAlign='left' size='medium'>Connections</Header>
              </Menu.Item>
              
              <Menu.Menu position='right'>
                <Menu.Item>
                  <NewConnectionModal />
                </Menu.Item>
              </Menu.Menu>
            </Menu>
          </Menu.Header>

          <Menu.Item>No connections.</Menu.Item>
        </Menu.Item>
    )
  }
}
