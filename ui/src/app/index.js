//
//  index.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/27/19
//  Copyright 2019 Wess Cope
//

import React from 'react'

import {
  BrowserRouter as Router,
  Route,
  Switch
} from 'react-router-dom'

import {
  Grid,
  Menu
} from 'semantic-ui-react'

import {
  Connections,
  Terminal,
  Summary
} from './components'

export default class App extends React.Component {
  constructor(props) {
    super(props)

    this.renderMasterColumn = this.renderMasterColumn.bind(this)
  }

  renderMasterColumn() {
    return (
      <Menu vertical compact borderless fluid style={{border: 'none', boxShadow: 'none'}}>
        <Connections/>
      </Menu>
    )
  }

  render() {
    return (
      <Router>
        <Grid id="main-view" columns={2} celled style={{margin: 0, padding: 0, height: '100%', minHeight: '100%', maxHeight: '100%'}}>
          <Grid.Row>

            <Grid.Column id="master-column" style={{background: 'white', flex: '0 0 200px'}}>
              {this.renderMasterColumn()}
            </Grid.Column>

            <Grid.Column id="detail-column">
              <Switch>
                <Route exact path="/" component={Summary}/>
                <Route path="/terminal" component={Terminal}/>
              </Switch>
            </Grid.Column>

          </Grid.Row>
        </Grid>
      </Router>
    )
  }
}
